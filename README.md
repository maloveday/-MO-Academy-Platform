# mo-academy

Monorepo for the MO Academy platform — a training business for CCSDS Mission
Operations (MO) services. Sells a self-paced course ($399), cohort seats
($1,600), and consulting; lead magnet is the "MO in 30 Minutes" primer.

## Architecture

```
                          ┌────────────────────────────────────────────────┐
                          │                  single VPS                    │
   students / leads       │  ┌───────┐      ┌──────────────────────────┐   │
  ────────browser───────▶ │  │ Caddy │────▶ │   api container (:8000)  │   │
                          │  │ :443  │      │  FastAPI                 │   │
                          │  └───────┘      │  ├─ static web (apps/web)│   │
                          │   TLS, HTTP/2   │  ├─ funnel + auth + LMS  │   │
                          │                 │  ├─ admin API            │   │
                          │                 │  └─ lab grading ─────────┼─┐ │
                          │                 └──────────┬───────────────┘ │ │
                          │                            │ SQLAlchemy      │ │
                          │                 ┌──────────▼───────────────┐ │ │
                          │                 │ SQLite volume (/data)    │ │ │
                          │                 │ (Postgres-ready via      │ │ │
                          │                 │  DATABASE_URL)           │ │ │
                          │                 └──────────────────────────┘ │ │
                          │  ┌──────────────────────────────────────┐    │ │
                          │  │ grader sandbox (docker run --rm)     │◀───┘ │
                          │  │ --network=none, mem/cpu/pid limits   │      │
                          │  │ image: mo-academy-grader             │      │
                          │  └──────────────────────────────────────┘      │
                          └────────────────────────────────────────────────┘

  SMTP (confirmations, primer, magic links) ──▶ your provider (EMAIL_BACKEND=smtp)
```

## Layout

```
apps/
  api/          FastAPI backend: funnel, magic-link auth, LMS, grading API, admin
    app/        application code
    alembic/    DB migrations (idempotent; `alembic upgrade head`)
    tests/      pytest suite
  web/          static frontend (amber-on-black console aesthetic)
    index.html      marketing site + signup funnel
    login.html      magic-link sign-in
    dashboard.html  student dashboard (lessons, quizzes, lab grading)
    admin.html      ops panel (metrics, leads, grading queue, cohorts)
content/        course content (syllabus, primer) — the seeder parses the syllabus
labs/           gradable labs (lab.json, starter, reference tests, passing example)
packages/
  mo_teach/     teaching library: broker, Parameter/Action services, grading harness
infra/          grader sandbox Dockerfile
.github/        CI: lint, tests, migration check, docker build + smoke test
```

## Run it

```sh
cp .env.example .env   # optional; sensible dev defaults are baked in
docker compose up --build
```

- Site: http://localhost:8000 · API docs: http://localhost:8000/docs
- Student dashboard: http://localhost:8000/dashboard.html (sign in first)
- Ops panel: http://localhost:8000/admin.html (needs `ADMIN_TOKEN`)

In dev, all email (double-opt-in confirmations, the primer, magic links) is
printed to the container log (`EMAIL_BACKEND=console`) — copy links out of
the log to click them. Startup runs `alembic upgrade head` and the curriculum
seeder; both are idempotent.

### Without Docker

```sh
cd apps/api
python -m venv .venv && . .venv/bin/activate
pip install -e ../../packages/mo_teach -e '.[dev]'
alembic upgrade head && python -m app.seed
uvicorn app.main:app --reload
```

### Grade a lab from the CLI

```sh
grade labs/lab-3-3/examples/passing --lab labs/lab-3-3
grade my-work/ --lab labs/lab-3-4 --mode docker --json rubric.json
```

## Tests

```sh
python -m pytest packages/mo_teach/tests -q   # library + grading harness self-test
cd apps/api && python -m pytest -q            # funnel, auth, LMS, labs, admin
```

CI (GitHub Actions) runs ruff, both suites, a double-apply migration + seed
check, docker builds of the API and grader images, and an HTTP smoke test.

## Configuration

All via environment (see `.env.example`). Never commit a real `.env`.

| Var | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | sqlite file | SQLAlchemy URL; Postgres-ready |
| `BASE_URL` | `http://localhost:8000` | absolute links in emails |
| `EMAIL_BACKEND` | `console` | `console` logs, `smtp` sends (`SMTP_*` vars) |
| `ADMIN_TOKEN` | *(unset)* | required for `/api/admin/*`; all admin access refused when unset |
| `PAYMENTS_ENABLED` | `false` | `false` = checkout falls back to a waitlist |
| `COOKIE_SECURE` | `false` | set `true` behind HTTPS |
| `GRADER_MODE` | `subprocess` | `docker` = sandboxed grading (production) |
| `GRADER_IMAGE` | `mo-academy-grader` | sandbox image for docker mode |
| `GRADER_TIMEOUT` | `180` | grading timeout (seconds) |

> **Grading sandbox:** `subprocess` mode executes student code with the API's
> privileges — dev only. In production set `GRADER_MODE=docker`, build the
> grader image, and give the api container access to the Docker socket (see
> `docker-compose.yml` comments). The sandbox runs with `--network=none`,
> memory/CPU/PID limits, and a non-root user.

## Deploying to a single VPS (Caddy)

1. Provision a small VPS (1–2 GB RAM), install Docker + compose, clone the repo.
2. `cp .env.example .env` and set at minimum:
   `BASE_URL=https://your.domain`, `EMAIL_BACKEND=smtp` + `SMTP_*`,
   a strong `ADMIN_TOKEN`, `COOKIE_SECURE=true`, `GRADER_MODE=docker`.
3. Build the grader sandbox image and start the stack:

   ```sh
   docker build -f infra/grader.Dockerfile -t mo-academy-grader .
   docker compose up -d --build
   ```

4. Install Caddy on the host and reverse-proxy with automatic TLS:

   ```caddy
   your.domain {
       reverse_proxy localhost:8000
       encode gzip
   }
   ```

5. Back up the SQLite volume (`docker volume inspect mo-academy_api-data`)
   on a cron, or point `DATABASE_URL` at managed Postgres
   (`postgresql+psycopg://...`) — the models and migrations are
   Postgres-compatible.

Uploads of lesson videos are out of scope here: set each lesson's
`video_url` to wherever you host them (any direct MP4/HLS URL works in the
dashboard player).

## Phase status

- [x] **Phase 1 — Marketing site + funnel**: landing page, `POST /api/signup`,
      double-opt-in confirm link, primer delivery via configurable SMTP
      (console in dev), admin CSV export, checkout stub with waitlist
      fallback (`PAYMENTS_ENABLED=false`).
- [x] **Phase 2 — Course platform (LMS-lite)**: email magic-link login,
      Course → Module → Lesson → Lab data model seeded from
      `content/syllabus_full.md` (idempotent), student dashboard with
      progress tracking, markdown lesson viewer, quiz engine with stored
      attempts.
- [x] **Phase 3 — Lab grading harness**: `packages/mo_teach` (broker,
      Parameter/Action provider + consumer), pytest-based reference consumers
      with rubric markers, `grade` CLI, sandboxed docker grading mode, lab
      submit/results in the dashboard, labs 3.3 and 3.4 fully working.
      Rubric: correctness / pattern usage / entity separation.
- [x] **Phase 4 — Ops**: admin panel (metrics, leads, grading queue with
      regrade, cohort management, student roster), GitHub Actions CI,
      architecture + deploy docs.

## Notes

- `packages/mo_teach/mo_mc_boilerplate.py` is kept as a compatibility shim —
  the course boilerplate now lives in the `mo_teach` package it grew into.
- The primer (`content/mo_in_30_minutes_primer.md`) still contains
  `[Your Business Name]` and `[Course link]` placeholders; whatever is in
  that file is exactly what gets emailed.
- First sign-in auto-creates the student account while payments are stubbed;
  gate it on purchase when checkout goes live (marked in
  `app/routers/auth.py` and `app/routers/course.py`).
