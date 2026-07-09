"""Admin-only endpoints, guarded by the X-Admin-Token header.

Serves the ops panel (/admin.html): lead list + CSV export, revenue/waitlist
metrics, the lab grading queue, cohort management, and the student roster.
"""

import csv
import io
import secrets
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models import (
    Cohort,
    Course,
    Enrollment,
    LabSubmission,
    Lead,
    Lesson,
    LessonProgress,
    User,
)
from app.routers.labs import run_grading

PRICES_USD = {"self_paced": 399, "cohort": 1600}


def require_admin(
    settings: Annotated[Settings, Depends(get_settings)],
    x_admin_token: Annotated[str, Header()] = "",
) -> None:
    if not settings.admin_token or not secrets.compare_digest(
        x_admin_token, settings.admin_token
    ):
        raise HTTPException(status_code=403, detail="Admin token required.")


router = APIRouter(
    prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)]
)


# --- Leads ---


@router.get("/leads")
def list_leads(db: Annotated[Session, Depends(get_db)]) -> list[dict[str, Any]]:
    return [
        {
            "id": lead.id,
            "email": lead.email,
            "source": lead.source,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
            "confirmed": lead.is_confirmed,
        }
        for lead in db.scalars(select(Lead).order_by(Lead.created_at.desc()))
    ]


@router.get("/leads.csv", response_class=PlainTextResponse)
def export_leads_csv(db: Annotated[Session, Depends(get_db)]) -> PlainTextResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["id", "email", "source", "created_at", "confirmed_at", "primer_sent_at"]
    )
    for lead in db.scalars(select(Lead).order_by(Lead.created_at)):
        writer.writerow(
            [
                lead.id,
                lead.email,
                lead.source,
                lead.created_at.isoformat() if lead.created_at else "",
                lead.confirmed_at.isoformat() if lead.confirmed_at else "",
                lead.primer_sent_at.isoformat() if lead.primer_sent_at else "",
            ]
        )
    return PlainTextResponse(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="leads.csv"'},
    )


# --- Metrics ---


@router.get("/metrics")
def metrics(db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    total_leads = db.scalar(select(func.count(Lead.id))) or 0
    confirmed = (
        db.scalar(
            select(func.count(Lead.id)).where(Lead.confirmed_at.is_not(None))
        )
        or 0
    )

    waitlist: dict[str, int] = {}
    for source, count in db.execute(
        select(Lead.source, func.count(Lead.id))
        .where(Lead.source.like("waitlist:%"))
        .group_by(Lead.source)
    ):
        waitlist[source.removeprefix("waitlist:")] = count

    revenue = {
        product: waitlist.get(product, 0) * price
        for product, price in PRICES_USD.items()
    }

    students = db.scalar(select(func.count(User.id))) or 0
    submissions_by_status: dict[str, int] = dict(
        db.execute(
            select(LabSubmission.status, func.count(LabSubmission.id)).group_by(
                LabSubmission.status
            )
        ).all()
    )
    completions = db.scalar(select(func.count(LessonProgress.id))) or 0

    return {
        "leads": {"total": total_leads, "confirmed": confirmed},
        "waitlist": waitlist,
        "revenue_potential_usd": {**revenue, "total": sum(revenue.values())},
        "students": {"total": students, "lesson_completions": completions},
        "submissions": submissions_by_status,
    }


# --- Grading queue ---


@router.get("/submissions")
def grading_queue(
    db: Annotated[Session, Depends(get_db)],
    status: str | None = None,
) -> list[dict[str, Any]]:
    query = (
        select(LabSubmission, User.email, Lesson.code)
        .join(User, User.id == LabSubmission.user_id)
        .join(Lesson, Lesson.id == LabSubmission.lesson_id)
        .order_by(LabSubmission.id.desc())
        .limit(200)
    )
    if status:
        query = query.where(LabSubmission.status == status)
    out: list[dict[str, Any]] = []
    for submission, email, lesson_code in db.execute(query):
        rubric = submission.rubric or {}
        out.append(
            {
                "id": submission.id,
                "student": email,
                "lesson": lesson_code,
                "status": submission.status,
                "score": rubric.get("score"),
                "passed": rubric.get("passed"),
                "error": rubric.get("error"),
                "created_at": submission.created_at.isoformat(),
            }
        )
    return out


@router.post("/submissions/{submission_id}/regrade")
def regrade_submission(
    submission_id: int,
    background: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    submission = db.get(LabSubmission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="No such submission.")
    submission.status = "queued"
    submission.rubric = None
    submission.graded_at = None
    db.commit()
    background.add_task(run_grading, submission.id)
    return {"id": submission.id, "status": "queued"}


# --- Cohorts ---


class CohortPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    starts_on: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    seats: int = Field(default=10, ge=1, le=500)


def _cohort_out(db: Session, cohort: Cohort) -> dict[str, Any]:
    members = (
        db.scalar(
            select(func.count(Enrollment.id)).where(
                Enrollment.cohort_id == cohort.id
            )
        )
        or 0
    )
    return {
        "id": cohort.id,
        "name": cohort.name,
        "starts_on": cohort.starts_on,
        "seats": cohort.seats,
        "members": members,
    }


@router.get("/cohorts")
def list_cohorts(db: Annotated[Session, Depends(get_db)]) -> list[dict[str, Any]]:
    return [
        _cohort_out(db, cohort)
        for cohort in db.scalars(select(Cohort).order_by(Cohort.id))
    ]


@router.post("/cohorts")
def create_cohort(
    payload: CohortPayload, db: Annotated[Session, Depends(get_db)]
) -> dict[str, Any]:
    if db.scalar(select(Cohort.id).where(Cohort.name == payload.name)) is not None:
        raise HTTPException(status_code=409, detail="Cohort name already exists.")
    cohort = Cohort(
        name=payload.name, starts_on=payload.starts_on, seats=payload.seats
    )
    db.add(cohort)
    db.commit()
    db.refresh(cohort)
    return _cohort_out(db, cohort)


class AssignPayload(BaseModel):
    email: EmailStr


@router.post("/cohorts/{cohort_id}/assign")
def assign_to_cohort(
    cohort_id: int,
    payload: AssignPayload,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    cohort = db.get(Cohort, cohort_id)
    if cohort is None:
        raise HTTPException(status_code=404, detail="No such cohort.")
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None:
        raise HTTPException(
            status_code=404,
            detail="No student with that email (they must sign in once first).",
        )

    members = (
        db.scalar(
            select(func.count(Enrollment.id)).where(Enrollment.cohort_id == cohort.id)
        )
        or 0
    )

    enrollment = db.scalar(
        select(Enrollment).where(Enrollment.user_id == user.id)
    )
    if enrollment is None:
        course = db.scalar(select(Course))
        if course is None:
            raise HTTPException(status_code=503, detail="Course not seeded yet.")
        enrollment = Enrollment(user_id=user.id, course_id=course.id)
        db.add(enrollment)

    if enrollment.cohort_id != cohort.id and members >= cohort.seats:
        raise HTTPException(status_code=409, detail="Cohort is full.")
    enrollment.cohort_id = cohort.id
    enrollment.tier = "cohort"
    db.commit()
    return _cohort_out(db, cohort)


# --- Students ---


@router.get("/students")
def list_students(db: Annotated[Session, Depends(get_db)]) -> list[dict[str, Any]]:
    progress_counts: dict[int, int] = dict(
        db.execute(
            select(LessonProgress.user_id, func.count(LessonProgress.id)).group_by(
                LessonProgress.user_id
            )
        ).all()
    )
    rows = db.execute(
        select(User, Enrollment.tier, Cohort.name)
        .outerjoin(Enrollment, Enrollment.user_id == User.id)
        .outerjoin(Cohort, Cohort.id == Enrollment.cohort_id)
        .order_by(User.id)
    )
    return [
        {
            "id": user.id,
            "email": user.email,
            "tier": tier,
            "cohort": cohort_name,
            "lessons_completed": progress_counts.get(user.id, 0),
            "last_login_at": (
                user.last_login_at.isoformat() if user.last_login_at else None
            ),
        }
        for user, tier, cohort_name in rows
    ]
