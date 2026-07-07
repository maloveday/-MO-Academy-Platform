"""Student dashboard API: course tree, lesson viewer, progress, quiz engine."""

from sqlalchemy import select

from app.models import Enrollment, QuizAttempt
from tests.conftest import ClientBundle, login


def test_course_requires_auth(seeded_client: ClientBundle) -> None:
    assert seeded_client.http.get("/api/course").status_code == 401
    assert seeded_client.http.get("/api/lessons/1.1").status_code == 401


def test_course_tree_shape_and_auto_enrollment(seeded_client: ClientBundle) -> None:
    login(seeded_client)
    res = seeded_client.http.get("/api/course")
    assert res.status_code == 200
    tree = res.json()

    assert tree["course"]["title"] == "CCSDS MO Service Framework"
    assert len(tree["modules"]) == 4
    assert [len(m["lessons"]) for m in tree["modules"]] == [4, 4, 4, 4]
    assert tree["progress"] == {"completed": 0, "total": 16}

    lesson_33 = tree["modules"][2]["lessons"][2]
    assert lesson_33["code"] == "3.3"
    assert lesson_33["has_lab"] is True
    assert lesson_33["quiz_questions"] == 2

    with seeded_client.session_factory() as db:
        assert db.scalar(select(Enrollment)) is not None


def test_lesson_detail_renders_markdown(seeded_client: ClientBundle) -> None:
    login(seeded_client)
    res = seeded_client.http.get("/api/lessons/3.3")
    assert res.status_code == 200
    lesson = res.json()

    assert lesson["title"] == "Parameter service deep dive"
    assert "<h2>" in lesson["body_html"]
    assert lesson["lab"]["repo_template_url"].endswith("lab-3-3")
    # The quiz payload must never leak answers.
    assert lesson["quiz"], "expected seeded quiz for 3.3"
    assert all("correct_index" not in q for q in lesson["quiz"])


def test_unknown_lesson_404(seeded_client: ClientBundle) -> None:
    login(seeded_client)
    assert seeded_client.http.get("/api/lessons/9.9").status_code == 404


def test_progress_tracking(seeded_client: ClientBundle) -> None:
    login(seeded_client)
    res = seeded_client.http.post("/api/lessons/1.1/complete")
    assert res.status_code == 200
    # Idempotent double-complete
    assert seeded_client.http.post("/api/lessons/1.1/complete").status_code == 200

    tree = seeded_client.http.get("/api/course").json()
    assert tree["progress"] == {"completed": 1, "total": 16}
    assert tree["modules"][0]["lessons"][0]["completed"] is True

    detail = seeded_client.http.get("/api/lessons/1.1").json()
    assert detail["completed"] is True


def test_quiz_grading_and_storage(seeded_client: ClientBundle) -> None:
    login(seeded_client)
    # Lesson 3.3 seeds: correct answers are [2, 0].
    res = seeded_client.http.post(
        "/api/lessons/3.3/quiz", json={"answers": [2, 1]}
    )
    assert res.status_code == 200
    result = res.json()
    assert result == {"score": 1, "total": 2, "correct": [True, False]}

    res = seeded_client.http.post(
        "/api/lessons/3.3/quiz", json={"answers": [2, 0]}
    )
    assert res.json()["score"] == 2

    with seeded_client.session_factory() as db:
        attempts = db.scalars(select(QuizAttempt)).all()
        assert len(attempts) == 2
        assert attempts[0].answers == [2, 1]

    tree = seeded_client.http.get("/api/course").json()
    assert tree["modules"][2]["lessons"][2]["best_score"] == {"score": 2, "total": 2}
    detail = seeded_client.http.get("/api/lessons/3.3").json()
    assert detail["last_attempt"] == {"score": 2, "total": 2}


def test_quiz_validates_answer_count(seeded_client: ClientBundle) -> None:
    login(seeded_client)
    res = seeded_client.http.post("/api/lessons/3.3/quiz", json={"answers": [1]})
    assert res.status_code == 422


def test_quiz_missing_returns_404(seeded_client: ClientBundle) -> None:
    login(seeded_client)
    # Lesson 4.1 has no seeded quiz.
    res = seeded_client.http.post("/api/lessons/4.1/quiz", json={"answers": []})
    assert res.status_code == 404
