# mo-academy

Monorepo for the MO Academy platform — training business for CCSDS Mission
Operations (MO) services. Sells a self-paced course ($399), cohort seats
($1,600), and consulting; lead magnet is the "MO in 30 Minutes" primer.

## Layout

```
apps/
  api/          FastAPI backend (funnel, later: LMS + grading API)
    app/        application code
    alembic/    DB migrations (idempotent, `alembic upgrade head`)
    tests/      pytest suite
  web/          static marketing site (amber-on-black console aesthetic)
content/        course content assets (syllabus, primer) — replace placeholders
packages/
  mo_teach/     MO teaching library (Phase 3: broker, MC providers, grader)
```

> **Note:** `packages/mo_teach/mo_mc_boilerplate.py` is a working placeholder —
> overwrite it with the real boilerplate; nothing else needs to change. The
> landing page, syllabus, and primer are the provided assets (the landing
> page's signup form and waitlist buttons were wired to the API).

## Run it

```sh
cp .env.example .env   # optional; sensible dev defaults are baked in
docker compose up --build
```

Site: http://localhost:8000 — API docs: http://localhost:8000/docs

In dev, emails are printed to the container log (`EMAIL_BACKEND=console`).
Sign up on the page, copy the confirmation link out of the log, open it, and
the primer "arrives" the same way. Set `EMAIL_BACKEND=smtp` + the `SMTP_*`
vars for real delivery.

### Without Docker

```sh
cd apps/api
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --reload
```

## Phase status

- [x] **Phase 1 — Marketing site + funnel**: landing page, `POST /api/signup`,
      double-opt-in confirm link, primer delivery via configurable SMTP
      (console in dev), admin CSV export (`GET /api/admin/leads.csv`,
      `X-Admin-Token` header), checkout stub with waitlist fallback
      (`PAYMENTS_ENABLED=false`).
- [x] **Phase 2 — Course platform (LMS-lite)**: email magic-link login
      (`/login.html`), Course → Module → Lesson → Lab data model seeded from
      `content/syllabus_full.md` (`python -m app.seed`, idempotent), student
      dashboard (`/dashboard.html`) with progress tracking, markdown lesson
      viewer, and a multiple-choice quiz engine with stored attempts.
- [ ] Phase 3 — Lab grading harness (`mo_teach`, sandboxed grader, 2 labs)
- [ ] Phase 4 — Ops (admin panel, CI, deploy notes)

## Tests

```sh
cd apps/api && pytest
```

Covers the signup flow (capture → confirm → primer, idempotency, token
rotation), checkout waitlist stub, admin export auth, magic-link auth
(single-use, expiry, sessions, logout), syllabus seeding, progress
tracking, and quiz grading.

## Configuration

All via environment (see `.env.example`). Never commit a real `.env`.

| Var | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | sqlite file | SQLAlchemy URL; Postgres-ready |
| `EMAIL_BACKEND` | `console` | `console` logs, `smtp` sends |
| `ADMIN_TOKEN` | *(unset)* | required for `/api/admin/*`; endpoints refuse all access when unset |
| `PAYMENTS_ENABLED` | `false` | `false` = checkout falls back to waitlist |
| `BASE_URL` | `http://localhost:8000` | used in confirmation links |
