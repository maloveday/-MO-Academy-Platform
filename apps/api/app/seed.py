"""Seed the curriculum from content/syllabus_full.md.

Parses the syllabus structure — ``## Module N — Title`` headings,
``**Outcome:**`` lines, and lesson table rows ``| 1.1 | lesson | lab |`` —
into Course → Module → Lesson → Lab records. Idempotent: re-running updates
titles/outcomes in place and never duplicates rows. Quiz questions (from
``seed_quizzes.py``) are only inserted for lessons that have none.

Run with: python -m app.seed
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Course, Lab, Lesson, Module, QuizQuestion
from app.seed_quizzes import QUIZZES

logger = logging.getLogger("mo_academy.seed")

COURSE_SLUG = "ccsds-mo"

_H1_RE = re.compile(r"^# (?P<title>.+?)(?: — .*)?$")
_MODULE_RE = re.compile(r"^## Module (?P<number>\d+) — (?P<title>.+)$")
_OUTCOME_RE = re.compile(r"^\*\*Outcome:\*\* (?P<outcome>.+)$")
_ROW_RE = re.compile(
    r"^\|\s*(?P<code>\d+\.\d+)\s*\|\s*(?P<lesson>.+?)\s*\|\s*(?P<lab>.+?)\s*\|$"
)


@dataclass
class ParsedLesson:
    code: str
    title: str
    detail: str
    lab_title: str


@dataclass
class ParsedModule:
    number: int
    title: str
    outcome: str = ""
    lessons: list[ParsedLesson] = field(default_factory=list)


@dataclass
class ParsedSyllabus:
    course_title: str
    description: str
    modules: list[ParsedModule] = field(default_factory=list)


def parse_syllabus(path: Path) -> ParsedSyllabus:
    course_title = "MO Academy Course"
    description = ""
    modules: list[ParsedModule] = []
    current: ParsedModule | None = None

    for line in path.read_text(encoding="utf-8").splitlines():
        if m := _MODULE_RE.match(line):
            current = ParsedModule(
                number=int(m["number"]), title=m["title"].strip()
            )
            modules.append(current)
        elif m := _H1_RE.match(line):
            course_title = m["title"].strip()
        elif (m := _OUTCOME_RE.match(line)) and current is not None:
            current.outcome = m["outcome"].strip()
        elif (m := _ROW_RE.match(line)) and current is not None:
            lesson_text = m["lesson"]
            title, _, detail = lesson_text.partition(": ")
            current.lessons.append(
                ParsedLesson(
                    code=m["code"],
                    title=title.strip(),
                    detail=detail.strip(),
                    lab_title=m["lab"].strip(),
                )
            )
        elif not description and line.startswith("Format:"):
            description = line.strip()

    if not modules:
        raise ValueError(f"no modules found in {path} — unexpected syllabus format")
    return ParsedSyllabus(
        course_title=course_title, description=description, modules=modules
    )


def _lesson_body(lesson: ParsedLesson) -> str:
    detail = f"{lesson.detail[:1].upper()}{lesson.detail[1:]}" if lesson.detail else ""
    parts: list[str] = []
    if detail:
        parts += ["## Overview", "", f"{detail}.", ""]
    parts += [
        "## Lab",
        "",
        f"**{lesson.lab_title}**",
        "",
        "Starter repository and automated grading arrive with the lab harness.",
    ]
    return "\n".join(parts)


def seed(db: Session, syllabus_path: Path) -> Course:
    parsed = parse_syllabus(syllabus_path)

    course = db.scalar(select(Course).where(Course.slug == COURSE_SLUG))
    if course is None:
        course = Course(slug=COURSE_SLUG, title=parsed.course_title)
        db.add(course)
        db.flush()
    course.title = parsed.course_title
    course.description = parsed.description

    for pm in parsed.modules:
        module = db.scalar(
            select(Module).where(
                Module.course_id == course.id, Module.number == pm.number
            )
        )
        if module is None:
            module = Module(course_id=course.id, number=pm.number, title=pm.title)
            db.add(module)
            db.flush()
        module.title = pm.title
        module.outcome = pm.outcome

        for position, pl in enumerate(pm.lessons, start=1):
            lesson = db.scalar(
                select(Lesson).where(
                    Lesson.module_id == module.id, Lesson.code == pl.code
                )
            )
            if lesson is None:
                lesson = Lesson(
                    module_id=module.id,
                    code=pl.code,
                    position=position,
                    title=pl.title,
                )
                db.add(lesson)
                db.flush()
            lesson.position = position
            lesson.title = pl.title
            lesson.body_md = _lesson_body(pl)

            lab = db.scalar(select(Lab).where(Lab.lesson_id == lesson.id))
            if lab is None:
                lab = Lab(lesson_id=lesson.id, title=pl.lab_title)
                db.add(lab)
            lab.title = pl.lab_title
            if not lab.repo_template_url:
                lab.repo_template_url = (
                    f"https://github.com/mo-academy/lab-{pl.code.replace('.', '-')}"
                )
            if not lab.grading_spec:
                lab.grading_spec = {
                    "harness": "mo_teach",
                    "rubric": {
                        "correctness": 0.5,
                        "pattern_usage": 0.3,
                        "entity_separation": 0.2,
                    },
                }

            existing_questions = db.scalar(
                select(QuizQuestion.id).where(QuizQuestion.lesson_id == lesson.id)
            )
            if existing_questions is None:
                for q_pos, (prompt, choices, correct) in enumerate(
                    QUIZZES.get(pl.code, []), start=1
                ):
                    db.add(
                        QuizQuestion(
                            lesson_id=lesson.id,
                            position=q_pos,
                            prompt=prompt,
                            choices=choices,
                            correct_index=correct,
                        )
                    )

    db.commit()
    return course


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    from app.db import SessionLocal

    settings = get_settings()
    syllabus = settings.content_dir / "syllabus_full.md"
    with SessionLocal() as db:
        course = seed(db, syllabus)
        n_modules = len(course.modules)
        n_lessons = sum(len(m.lessons) for m in course.modules)
        logger.info(
            "seeded course %r: %d modules, %d lessons", course.title, n_modules, n_lessons
        )


if __name__ == "__main__":
    main()
