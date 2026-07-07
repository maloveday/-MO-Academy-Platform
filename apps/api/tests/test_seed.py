"""Seeder: parses the real syllabus into the curriculum tables, idempotently."""

from sqlalchemy import select

from app.config import get_settings
from app.models import Course, Lab, Lesson, Module, QuizQuestion
from app.seed import parse_syllabus, seed
from tests.conftest import ClientBundle

SYLLABUS = get_settings().content_dir / "syllabus_full.md"


def test_parse_syllabus_structure() -> None:
    parsed = parse_syllabus(SYLLABUS)
    assert parsed.course_title == "CCSDS MO Service Framework"
    assert len(parsed.modules) == 4
    assert all(len(m.lessons) == 4 for m in parsed.modules)
    assert all(m.outcome for m in parsed.modules)

    lesson_33 = parsed.modules[2].lessons[2]
    assert lesson_33.code == "3.3"
    assert lesson_33.title == "Parameter service deep dive"
    assert "dashboard" in lesson_33.lab_title


def test_seed_creates_full_curriculum(client: ClientBundle) -> None:
    with client.session_factory() as db:
        seed(db, SYLLABUS)

        course = db.scalar(select(Course))
        assert course.slug == "ccsds-mo"
        assert len(db.scalars(select(Module)).all()) == 4
        lessons = db.scalars(select(Lesson)).all()
        assert len(lessons) == 16
        assert len(db.scalars(select(Lab)).all()) == 16
        assert all(lesson.body_md for lesson in lessons)

        # Quizzes seeded where defined
        quiz_lessons = {
            db.get(Lesson, q.lesson_id).code
            for q in db.scalars(select(QuizQuestion))
        }
        assert {"3.3", "3.4", "2.1"} <= quiz_lessons


def test_seed_is_idempotent(client: ClientBundle) -> None:
    with client.session_factory() as db:
        seed(db, SYLLABUS)
        seed(db, SYLLABUS)

        assert len(db.scalars(select(Course)).all()) == 1
        assert len(db.scalars(select(Module)).all()) == 4
        assert len(db.scalars(select(Lesson)).all()) == 16
        assert len(db.scalars(select(Lab)).all()) == 16
