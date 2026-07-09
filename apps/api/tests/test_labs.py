"""Lab submission API: submit, background grading, results on the dashboard."""

from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.models import LabSubmission
from tests.conftest import ClientBundle, login

PASSING_33 = (
    get_settings().labs_dir / "lab-3-3" / "examples" / "passing" / "solution.py"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_submit_requires_auth(seeded_client: ClientBundle) -> None:
    res = seeded_client.http.post(
        "/api/lessons/3.3/lab/submit", json={"content": "x = 1"}
    )
    assert res.status_code == 401


def test_submit_rejected_for_non_gradable_lesson(seeded_client: ClientBundle) -> None:
    login(seeded_client)
    res = seeded_client.http.post(
        "/api/lessons/1.1/lab/submit", json={"content": "x = 1"}
    )
    assert res.status_code == 404
    assert "no gradable lab" in res.json()["detail"]


def test_lesson_detail_reports_gradable_labs(seeded_client: ClientBundle) -> None:
    login(seeded_client)
    assert seeded_client.http.get("/api/lessons/3.3").json()["lab"]["gradable"] is True
    assert seeded_client.http.get("/api/lessons/1.1").json()["lab"]["gradable"] is False


def test_passing_submission_graded_full_score(seeded_client: ClientBundle) -> None:
    login(seeded_client)
    res = seeded_client.http.post(
        "/api/lessons/3.3/lab/submit", json={"content": _read(PASSING_33)}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "queued"

    # TestClient runs background tasks before returning control, so the
    # grading has completed by now.
    subs = seeded_client.http.get("/api/lessons/3.3/lab/submissions").json()
    assert len(subs) == 1
    latest = subs[0]
    assert latest["status"] == "graded"
    assert latest["score"] == 1.0
    assert latest["passed"] is True
    assert set(latest["categories"]) == {
        "correctness",
        "pattern_usage",
        "entity_separation",
    }

    with seeded_client.session_factory() as db:
        stored = db.scalar(select(LabSubmission))
        assert stored.status == "graded"
        assert stored.graded_at is not None


def test_broken_submission_graded_as_fail_not_error(
    seeded_client: ClientBundle,
) -> None:
    login(seeded_client)
    seeded_client.http.post(
        "/api/lessons/3.4/lab/submit",
        json={"content": "def register_set_heater_state(p, h):\n    pass\n"},
    )
    latest = seeded_client.http.get("/api/lessons/3.4/lab/submissions").json()[0]
    assert latest["status"] == "graded"
    assert latest["passed"] is False
    assert latest["score"] < 0.7


def test_submission_size_limit(seeded_client: ClientBundle) -> None:
    login(seeded_client)
    res = seeded_client.http.post(
        "/api/lessons/3.3/lab/submit", json={"content": "#" * 200_000}
    )
    assert res.status_code == 422


def test_submissions_listed_newest_first(seeded_client: ClientBundle) -> None:
    login(seeded_client)
    seeded_client.http.post("/api/lessons/3.3/lab/submit", json={"content": "x = 1"})
    seeded_client.http.post(
        "/api/lessons/3.3/lab/submit", json={"content": _read(PASSING_33)}
    )
    subs = seeded_client.http.get("/api/lessons/3.3/lab/submissions").json()
    assert len(subs) == 2
    assert subs[0]["id"] > subs[1]["id"]
    assert subs[0]["passed"] is True
