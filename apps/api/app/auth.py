"""Magic-link auth: token issuance, session cookies, current-user dependency."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import MagicLinkToken, SessionToken, User, utcnow

COOKIE_NAME = "mo_session"
MAGIC_LINK_TTL = timedelta(minutes=30)
SESSION_TTL = timedelta(days=30)


def as_utc(dt: datetime) -> datetime:
    """Normalise DB datetimes: SQLite returns naive UTC, Postgres returns aware."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def create_magic_link_token(db: Session, user: User) -> MagicLinkToken:
    token = MagicLinkToken(user_id=user.id, expires_at=utcnow() + MAGIC_LINK_TTL)
    db.add(token)
    db.flush()
    return token


def redeem_magic_link_token(db: Session, raw_token: str) -> User | None:
    """Validate and consume a magic-link token; returns its user or None."""
    token = db.scalar(
        select(MagicLinkToken).where(MagicLinkToken.token == raw_token)
    )
    if token is None or token.used_at is not None:
        return None
    if as_utc(token.expires_at) < utcnow():
        return None
    token.used_at = utcnow()
    user = db.get(User, token.user_id)
    if user is not None:
        user.last_login_at = utcnow()
    return user


def create_session(db: Session, user: User) -> SessionToken:
    session = SessionToken(user_id=user.id, expires_at=utcnow() + SESSION_TTL)
    db.add(session)
    db.flush()
    return session


def get_current_user(
    request: Request, db: Annotated[Session, Depends(get_db)]
) -> User:
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        raise HTTPException(status_code=401, detail="Not signed in.")
    session = db.scalar(select(SessionToken).where(SessionToken.token == raw))
    if session is None or as_utc(session.expires_at) < utcnow():
        raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user.")
    return user
