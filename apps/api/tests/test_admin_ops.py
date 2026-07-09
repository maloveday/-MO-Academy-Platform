"""Phase 4 admin ops: metrics, grading queue, cohorts, students."""

from pathlib import Path

from app.config import get_settings
from tests.conftest import ClientBundle, login

HEADERS = {"X-Admin-Token": "test-admin-token"}

PASSING_33 = (
    get_settings().labs_dir / "lab-3-3" / "examples" / "passing" / "solution.py"
)


def test_admin_endpoints_require_token(seeded_client: ClientBundle) -> None:
    for path in (
        "/api/admin/leads",
        "/api/admin/metrics",
        "/api/admin/submissions",
        "/api/admin/cohorts",
        "/api/admin/students",
    ):
        assert seeded_client.http.get(path).status_code == 403, path


def test_metrics_aggregates(seeded_client: ClientBundle) -> None:
    seeded_client.http.post("/api/signup", json={"email": "lead@example.com"})
    seeded_client.http.post(
        "/api/checkout", json={"email": "buyer@example.com", "product": "cohort"}
    )
    login(seeded_client)
    seeded_client.http.post("/api/lessons/1.1/complete")

    m = seeded_client.http.get("/api/admin/metrics", headers=HEADERS).json()
    assert m["leads"]["total"] == 2
    assert m["waitlist"] == {"cohort": 1}
    assert m["revenue_potential_usd"]["cohort"] == 1600
    assert m["revenue_potential_usd"]["total"] == 1600
    assert m["students"]["total"] == 1
    assert m["students"]["lesson_completions"] == 1


def test_grading_queue_and_regrade(seeded_client: ClientBundle) -> None:
    login(seeded_client)
    seeded_client.http.post(
        "/api/lessons/3.3/lab/submit",
        json={"content": Path(PASSING_33).read_text(encoding="utf-8")},
    )

    queue = seeded_client.http.get("/api/admin/submissions", headers=HEADERS).json()
    assert len(queue) == 1
    entry = queue[0]
    assert entry["student"] == "student@example.com"
    assert entry["lesson"] == "3.3"
    assert entry["status"] == "graded"
    assert entry["passed"] is True

    res = seeded_client.http.post(
        f"/api/admin/submissions/{entry['id']}/regrade", headers=HEADERS
    )
    assert res.status_code == 200
    requeued = seeded_client.http.get(
        "/api/admin/submissions", headers=HEADERS
    ).json()[0]
    assert requeued["status"] == "graded"  # background regrade already ran
    assert requeued["passed"] is True

    assert (
        seeded_client.http.post(
            "/api/admin/submissions/9999/regrade", headers=HEADERS
        ).status_code
        == 404
    )


def test_cohort_lifecycle(seeded_client: ClientBundle) -> None:
    login(seeded_client, "student@example.com")

    res = seeded_client.http.post(
        "/api/admin/cohorts",
        headers=HEADERS,
        json={"name": "2026-Q4", "starts_on": "2026-10-05", "seats": 2},
    )
    assert res.status_code == 200
    cohort = res.json()
    assert cohort["members"] == 0

    # Duplicate name rejected
    assert (
        seeded_client.http.post(
            "/api/admin/cohorts", headers=HEADERS, json={"name": "2026-Q4"}
        ).status_code
        == 409
    )

    res = seeded_client.http.post(
        f"/api/admin/cohorts/{cohort['id']}/assign",
        headers=HEADERS,
        json={"email": "student@example.com"},
    )
    assert res.status_code == 200
    assert res.json()["members"] == 1

    # Unknown student
    assert (
        seeded_client.http.post(
            f"/api/admin/cohorts/{cohort['id']}/assign",
            headers=HEADERS,
            json={"email": "ghost@example.com"},
        ).status_code
        == 404
    )

    students = seeded_client.http.get("/api/admin/students", headers=HEADERS).json()
    assert students[0]["email"] == "student@example.com"
    assert students[0]["cohort"] == "2026-Q4"
    assert students[0]["tier"] == "cohort"


def test_cohort_seat_limit(seeded_client: ClientBundle) -> None:
    cohort = seeded_client.http.post(
        "/api/admin/cohorts", headers=HEADERS, json={"name": "tiny", "seats": 1}
    ).json()

    login(seeded_client, "a@example.com")
    seeded_client.http.cookies.clear()
    login(seeded_client, "b@example.com")

    assert (
        seeded_client.http.post(
            f"/api/admin/cohorts/{cohort['id']}/assign",
            headers=HEADERS,
            json={"email": "a@example.com"},
        ).status_code
        == 200
    )
    res = seeded_client.http.post(
        f"/api/admin/cohorts/{cohort['id']}/assign",
        headers=HEADERS,
        json={"email": "b@example.com"},
    )
    assert res.status_code == 409
    assert "full" in res.json()["detail"]


def test_leads_json_listing(client: ClientBundle) -> None:
    client.http.post("/api/signup", json={"email": "lead@example.com"})
    leads = client.http.get("/api/admin/leads", headers=HEADERS).json()
    assert len(leads) == 1
    assert leads[0]["email"] == "lead@example.com"
    assert leads[0]["confirmed"] is False
