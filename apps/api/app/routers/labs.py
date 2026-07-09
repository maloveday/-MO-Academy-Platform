"""Lab submission + grading endpoints the dashboard calls."""

import logging
import tempfile
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import Settings, get_settings
from app.db import get_db
from app.models import Lab, LabSubmission, Lesson, User, utcnow

logger = logging.getLogger("mo_academy.labs")

router = APIRouter(prefix="/api/lessons", tags=["labs"])

MAX_SUBMISSION_BYTES = 100_000


def lab_dir_for(code: str, settings: Settings) -> Path:
    return settings.labs_dir / f"lab-{code.replace('.', '-')}"


def _get_gradable_lesson(db: Session, code: str, settings: Settings) -> Lesson:
    lesson = db.scalar(select(Lesson).where(Lesson.code == code))
    if lesson is None:
        raise HTTPException(status_code=404, detail=f"No lesson {code}.")
    lab = db.scalar(select(Lab).where(Lab.lesson_id == lesson.id))
    if lab is None or not (lab_dir_for(code, settings) / "lab.json").exists():
        raise HTTPException(
            status_code=404,
            detail=f"Lesson {code} has no gradable lab yet.",
        )
    return lesson


def run_grading(submission_id: int) -> None:
    """Grade one submission (background task; opens its own DB session)."""
    from app import db as app_db

    with app_db.SessionLocal() as db:
        submission = db.get(LabSubmission, submission_id)
        if submission is None:
            return
        lesson = db.get(Lesson, submission.lesson_id)
        settings = get_settings()
        submission.status = "running"
        db.commit()

        try:
            from mo_teach.grading.grader import grade_submission

            with tempfile.TemporaryDirectory(prefix="mo-submission-") as tmp:
                submission_dir = Path(tmp)
                (submission_dir / submission.filename).write_text(
                    submission.content, encoding="utf-8"
                )
                rubric: dict[str, Any] = grade_submission(
                    submission_dir,
                    lab_dir_for(lesson.code, settings),
                    mode=settings.grader_mode,
                    timeout=settings.grader_timeout,
                    docker_image=settings.grader_image,
                )
            submission.rubric = rubric
            submission.status = "error" if rubric.get("error") else "graded"
        except Exception as exc:  # harness failure must never wedge the queue
            logger.exception("grading submission %d failed", submission_id)
            submission.rubric = {"error": f"{type(exc).__name__}: {exc}"}
            submission.status = "error"
        submission.graded_at = utcnow()
        db.commit()


class SubmitPayload(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_SUBMISSION_BYTES)
    filename: str = Field(default="solution.py", pattern=r"^[\w.-]+\.py$")


def _submission_out(submission: LabSubmission) -> dict[str, Any]:
    rubric = submission.rubric or {}
    return {
        "id": submission.id,
        "status": submission.status,
        "filename": submission.filename,
        "created_at": submission.created_at.isoformat(),
        "graded_at": (
            submission.graded_at.isoformat() if submission.graded_at else None
        ),
        "score": rubric.get("score"),
        "passed": rubric.get("passed"),
        "categories": rubric.get("categories"),
        "error": rubric.get("error"),
    }


@router.post("/{code}/lab/submit")
def submit_lab(
    code: str,
    payload: SubmitPayload,
    background: BackgroundTasks,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    lesson = _get_gradable_lesson(db, code, settings)
    submission = LabSubmission(
        user_id=user.id,
        lesson_id=lesson.id,
        filename=payload.filename,
        content=payload.content,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    background.add_task(run_grading, submission.id)
    return _submission_out(submission)


@router.get("/{code}/lab/submissions")
def list_my_submissions(
    code: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict[str, Any]]:
    lesson = db.scalar(select(Lesson).where(Lesson.code == code))
    if lesson is None:
        raise HTTPException(status_code=404, detail=f"No lesson {code}.")
    submissions = db.scalars(
        select(LabSubmission)
        .where(
            LabSubmission.user_id == user.id,
            LabSubmission.lesson_id == lesson.id,
        )
        .order_by(LabSubmission.id.desc())
        .limit(10)
    )
    return [_submission_out(s) for s in submissions]
