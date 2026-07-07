"""Email capture funnel: signup, double-opt-in confirmation, primer delivery."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.emailer import EmailBackend, EmailMessage, get_email_backend
from app.models import Lead, new_token, utcnow
from app.pages import console_page

router = APIRouter(prefix="/api/signup", tags=["signup"])

CONFIRM_SUBJECT = "Confirm your email — MO Academy"
PRIMER_SUBJECT = "MO in 30 Minutes — your primer"


class SignupRequest(BaseModel):
    email: EmailStr
    source: str = Field(default="landing:primer", max_length=100)


class SignupResponse(BaseModel):
    status: str
    message: str


def _send_confirmation(
    lead: Lead, settings: Settings, emailer: EmailBackend
) -> None:
    link = f"{settings.base_url}/api/signup/confirm?token={lead.confirm_token}"
    body = (
        "You (or someone using this address) asked for the free primer\n"
        '"MO in 30 Minutes" from MO Academy.\n\n'
        f"Confirm your email to receive it:\n\n  {link}\n\n"
        "If this wasn't you, ignore this message and nothing will be sent."
    )
    emailer.send(EmailMessage(to=lead.email, subject=CONFIRM_SUBJECT, body=body))


def _send_primer(lead: Lead, settings: Settings, emailer: EmailBackend) -> None:
    primer_path = settings.content_dir / "mo_in_30_minutes_primer.md"
    body = primer_path.read_text(encoding="utf-8")
    emailer.send(EmailMessage(to=lead.email, subject=PRIMER_SUBJECT, body=body))
    lead.primer_sent_at = utcnow()


@router.post("", response_model=SignupResponse)
def signup(
    payload: SignupRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    emailer: Annotated[EmailBackend, Depends(get_email_backend)],
) -> SignupResponse:
    email = payload.email.lower()
    lead = db.scalar(select(Lead).where(Lead.email == email))

    if lead is None:
        lead = Lead(email=email, source=payload.source)
        db.add(lead)
        db.commit()
        db.refresh(lead)
    elif lead.is_confirmed:
        # Idempotent: don't leak whether an address is subscribed beyond this.
        return SignupResponse(
            status="ok", message="You're already confirmed. Check your inbox."
        )
    else:
        lead.confirm_token = new_token()
        db.commit()

    _send_confirmation(lead, settings, emailer)
    return SignupResponse(
        status="pending",
        message="Check your inbox and click the confirmation link.",
    )


@router.get("/confirm", response_class=HTMLResponse)
def confirm(
    token: str,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    emailer: Annotated[EmailBackend, Depends(get_email_backend)],
) -> HTMLResponse:
    lead = db.scalar(select(Lead).where(Lead.confirm_token == token))
    if lead is None:
        return HTMLResponse(
            console_page(
                "Link not recognised",
                "This confirmation link is invalid or expired. "
                "Sign up again to get a fresh one.",
            ),
            status_code=404,
        )

    if not lead.is_confirmed:
        lead.confirmed_at = utcnow()
    if lead.primer_sent_at is None:
        _send_primer(lead, settings, emailer)
    db.commit()

    return HTMLResponse(
        console_page(
            "Email confirmed",
            "You're in. “MO in 30 Minutes” is on its way to your inbox.",
        )
    )
