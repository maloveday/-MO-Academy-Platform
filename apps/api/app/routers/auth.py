"""Magic-link login endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    COOKIE_NAME,
    SESSION_TTL,
    create_magic_link_token,
    create_session,
    get_current_user,
    redeem_magic_link_token,
)
from app.config import Settings, get_settings
from app.db import get_db
from app.emailer import EmailBackend, EmailMessage, get_email_backend
from app.models import SessionToken, User
from app.pages import console_page

router = APIRouter(prefix="/api/auth", tags=["auth"])

LOGIN_SUBJECT = "Your sign-in link — MO Academy"


class RequestLinkPayload(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    status: str
    message: str


class MeResponse(BaseModel):
    id: int
    email: str


@router.post("/request-link", response_model=MessageResponse)
def request_link(
    payload: RequestLinkPayload,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    emailer: Annotated[EmailBackend, Depends(get_email_backend)],
) -> MessageResponse:
    email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        # Payments are stubbed, so first sign-in creates the account.
        # Once checkout is real, gate this on purchase/enrollment instead.
        user = User(email=email)
        db.add(user)
        db.flush()

    token = create_magic_link_token(db, user)
    db.commit()

    link = f"{settings.base_url}/api/auth/verify?token={token.token}"
    body = (
        "Sign in to MO Academy with this link (valid for 30 minutes,\n"
        f"single use):\n\n  {link}\n\n"
        "If you didn't request this, you can safely ignore it."
    )
    emailer.send(EmailMessage(to=email, subject=LOGIN_SUBJECT, body=body))
    return MessageResponse(
        status="sent", message="Check your inbox for a sign-in link."
    )


@router.get("/verify")
def verify(
    token: str,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    user = redeem_magic_link_token(db, token)
    if user is None:
        db.commit()
        return HTMLResponse(
            console_page(
                "Link not valid",
                "This sign-in link is invalid, expired, or already used. "
                'Request a fresh one from the <a href="/login.html">sign-in page</a>.',
            ),
            status_code=400,
        )

    session = create_session(db, user)
    db.commit()

    response = RedirectResponse("/dashboard.html", status_code=303)
    response.set_cookie(
        COOKIE_NAME,
        session.token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return response


@router.get("/me", response_model=MeResponse)
def me(user: Annotated[User, Depends(get_current_user)]) -> MeResponse:
    return MeResponse(id=user.id, email=user.email)


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    raw = request.cookies.get(COOKIE_NAME)
    if raw:
        session = db.scalar(
            select(SessionToken).where(SessionToken.token == raw)
        )
        if session is not None:
            db.delete(session)
            db.commit()
    response.delete_cookie(COOKIE_NAME)
    return MessageResponse(status="ok", message="Signed out.")
