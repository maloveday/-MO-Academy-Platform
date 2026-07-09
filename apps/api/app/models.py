"""SQLAlchemy models."""

import secrets
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_token() -> str:
    return secrets.token_urlsafe(32)


class Lead(Base):
    """An email lead captured from the marketing funnel.

    ``source`` records where the lead came from, e.g. ``landing:primer`` or
    ``waitlist:cohort``.
    """

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(100), default="unknown")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    confirm_token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=new_token
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    primer_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    @property
    def is_confirmed(self) -> bool:
        return self.confirmed_at is not None


# --- Auth ---


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class MagicLinkToken(Base):
    """Single-use, short-lived login token emailed to the user."""

    __tablename__ = "magic_link_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=new_token
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class SessionToken(Base):
    """Opaque bearer stored in an HttpOnly cookie."""

    __tablename__ = "session_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=new_token
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


# --- Curriculum ---


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")

    modules: Mapped[list["Module"]] = relationship(
        back_populates="course", order_by="Module.number"
    )


class Module(Base):
    __tablename__ = "modules"
    __table_args__ = (UniqueConstraint("course_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    number: Mapped[int] = mapped_column()
    title: Mapped[str] = mapped_column(String(200))
    outcome: Mapped[str] = mapped_column(Text, default="")

    course: Mapped[Course] = relationship(back_populates="modules")
    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="module", order_by="Lesson.position"
    )


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("module_id", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"))
    code: Mapped[str] = mapped_column(String(10), index=True)  # e.g. "3.3"
    position: Mapped[int] = mapped_column()
    title: Mapped[str] = mapped_column(String(300))
    video_url: Mapped[str | None] = mapped_column(String(500), default=None)
    body_md: Mapped[str] = mapped_column(Text, default="")

    module: Mapped[Module] = relationship(back_populates="lessons")
    lab: Mapped["Lab | None"] = relationship(back_populates="lesson")
    quiz_questions: Mapped[list["QuizQuestion"]] = relationship(
        back_populates="lesson", order_by="QuizQuestion.position"
    )


class Lab(Base):
    __tablename__ = "labs"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    repo_template_url: Mapped[str] = mapped_column(String(500), default="")
    grading_spec: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    lesson: Mapped[Lesson] = relationship(back_populates="lab")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    position: Mapped[int] = mapped_column()
    prompt: Mapped[str] = mapped_column(Text)
    choices: Mapped[list[str]] = mapped_column(JSON)
    correct_index: Mapped[int] = mapped_column()

    lesson: Mapped[Lesson] = relationship(back_populates="quiz_questions")


# --- Student state ---


class Cohort(Base):
    """A scheduled cohort run of the course."""

    __tablename__ = "cohorts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    starts_on: Mapped[str | None] = mapped_column(String(10), default=None)  # ISO date
    seats: Mapped[int] = mapped_column(default=10)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    tier: Mapped[str] = mapped_column(String(30), default="self_paced")
    cohort_id: Mapped[int | None] = mapped_column(
        ForeignKey("cohorts.id"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"))
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class LabSubmission(Base):
    """A student's lab submission and its grading state.

    ``status``: queued → running → graded, or error (harness failure —
    distinct from a graded-but-failing submission, which is status=graded
    with rubric.passed false).
    """

    __tablename__ = "lab_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    filename: Mapped[str] = mapped_column(String(100), default="solution.py")
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    rubric: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    graded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    score: Mapped[int] = mapped_column()
    total: Mapped[int] = mapped_column()
    answers: Mapped[list[int]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
