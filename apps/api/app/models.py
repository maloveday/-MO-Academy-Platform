"""SQLAlchemy models."""

import secrets
from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

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
