"""Student-facing course API: curriculum tree, lesson viewer, progress, quizzes."""

from typing import Annotated, Any

import markdown as md
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import (
    Course,
    Enrollment,
    Lesson,
    LessonProgress,
    Module,
    QuizAttempt,
    User,
)
from app.seed import COURSE_SLUG

router = APIRouter(prefix="/api", tags=["course"])


def _get_course(db: Session) -> Course:
    course = db.scalar(select(Course).where(Course.slug == COURSE_SLUG))
    if course is None:
        raise HTTPException(status_code=503, detail="Course not seeded yet.")
    return course


def _get_lesson(db: Session, code: str) -> Lesson:
    lesson = db.scalar(select(Lesson).where(Lesson.code == code))
    if lesson is None:
        raise HTTPException(status_code=404, detail=f"No lesson {code}.")
    return lesson


def _ensure_enrolled(db: Session, user: User, course: Course) -> None:
    # Payments are stubbed: first authenticated visit enrolls the student.
    # Replace with purchase-gated enrollment when checkout goes live.
    exists = db.scalar(
        select(Enrollment.id).where(
            Enrollment.user_id == user.id, Enrollment.course_id == course.id
        )
    )
    if exists is None:
        db.add(Enrollment(user_id=user.id, course_id=course.id))
        db.commit()


@router.get("/course")
def course_tree(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    course = _get_course(db)
    _ensure_enrolled(db, user, course)

    completed_ids = set(
        db.scalars(
            select(LessonProgress.lesson_id).where(LessonProgress.user_id == user.id)
        )
    )
    best_scores: dict[int, tuple[int, int]] = {
        lesson_id: (score, total)
        for lesson_id, score, total in db.execute(
            select(
                QuizAttempt.lesson_id,
                func.max(QuizAttempt.score),
                func.max(QuizAttempt.total),
            )
            .where(QuizAttempt.user_id == user.id)
            .group_by(QuizAttempt.lesson_id)
        )
    }

    modules_out: list[dict[str, Any]] = []
    total_lessons = 0
    for module in db.scalars(
        select(Module).where(Module.course_id == course.id).order_by(Module.number)
    ):
        lessons_out: list[dict[str, Any]] = []
        for lesson in module.lessons:
            total_lessons += 1
            best = best_scores.get(lesson.id)
            lessons_out.append(
                {
                    "code": lesson.code,
                    "title": lesson.title,
                    "completed": lesson.id in completed_ids,
                    "has_lab": lesson.lab is not None,
                    "quiz_questions": len(lesson.quiz_questions),
                    "best_score": (
                        {"score": best[0], "total": best[1]} if best else None
                    ),
                }
            )
        modules_out.append(
            {
                "number": module.number,
                "title": module.title,
                "outcome": module.outcome,
                "lessons": lessons_out,
            }
        )

    return {
        "course": {
            "slug": course.slug,
            "title": course.title,
            "description": course.description,
        },
        "modules": modules_out,
        "progress": {"completed": len(completed_ids), "total": total_lessons},
    }


@router.get("/lessons/{code}")
def lesson_detail(
    code: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    lesson = _get_lesson(db, code)

    completed = (
        db.scalar(
            select(LessonProgress.id).where(
                LessonProgress.user_id == user.id,
                LessonProgress.lesson_id == lesson.id,
            )
        )
        is not None
    )
    last_attempt = db.scalar(
        select(QuizAttempt)
        .where(QuizAttempt.user_id == user.id, QuizAttempt.lesson_id == lesson.id)
        .order_by(QuizAttempt.created_at.desc(), QuizAttempt.id.desc())
        .limit(1)
    )

    return {
        "code": lesson.code,
        "title": lesson.title,
        "module": {"number": lesson.module.number, "title": lesson.module.title},
        "video_url": lesson.video_url,
        "body_html": md.markdown(
            lesson.body_md, extensions=["tables", "fenced_code"]
        ),
        "lab": (
            {
                "title": lesson.lab.title,
                "repo_template_url": lesson.lab.repo_template_url,
            }
            if lesson.lab
            else None
        ),
        # Deliberately no correct_index: answers are graded server-side only.
        "quiz": [
            {"id": q.id, "prompt": q.prompt, "choices": q.choices}
            for q in lesson.quiz_questions
        ],
        "completed": completed,
        "last_attempt": (
            {"score": last_attempt.score, "total": last_attempt.total}
            if last_attempt
            else None
        ),
    }


class CompleteResponse(BaseModel):
    status: str
    completed: bool


@router.post("/lessons/{code}/complete", response_model=CompleteResponse)
def complete_lesson(
    code: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CompleteResponse:
    lesson = _get_lesson(db, code)
    exists = db.scalar(
        select(LessonProgress.id).where(
            LessonProgress.user_id == user.id, LessonProgress.lesson_id == lesson.id
        )
    )
    if exists is None:
        db.add(LessonProgress(user_id=user.id, lesson_id=lesson.id))
        db.commit()
    return CompleteResponse(status="ok", completed=True)


class QuizSubmission(BaseModel):
    answers: list[int]


class QuizResult(BaseModel):
    score: int
    total: int
    correct: list[bool]


@router.post("/lessons/{code}/quiz", response_model=QuizResult)
def submit_quiz(
    code: str,
    payload: QuizSubmission,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> QuizResult:
    lesson = _get_lesson(db, code)
    questions = lesson.quiz_questions
    if not questions:
        raise HTTPException(status_code=404, detail=f"Lesson {code} has no quiz.")
    if len(payload.answers) != len(questions):
        raise HTTPException(
            status_code=422,
            detail=f"Expected {len(questions)} answers, got {len(payload.answers)}.",
        )

    correct = [
        answer == question.correct_index
        for answer, question in zip(payload.answers, questions, strict=True)
    ]
    score = sum(correct)
    db.add(
        QuizAttempt(
            user_id=user.id,
            lesson_id=lesson.id,
            score=score,
            total=len(questions),
            answers=payload.answers,
        )
    )
    db.commit()
    return QuizResult(score=score, total=len(questions), correct=correct)
