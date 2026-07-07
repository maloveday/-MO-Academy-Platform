"""Checkout stub. With PAYMENTS_ENABLED=false, every product falls back to a waitlist."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models import Lead

router = APIRouter(prefix="/api/checkout", tags=["checkout"])

Product = Literal["self_paced", "cohort", "consulting"]

PRODUCT_LABELS: dict[str, str] = {
    "self_paced": "the self-paced course",
    "cohort": "the next cohort",
    "consulting": "consulting",
}


class CheckoutRequest(BaseModel):
    email: EmailStr
    product: Product


class CheckoutResponse(BaseModel):
    status: str
    message: str


@router.post("", response_model=CheckoutResponse)
def checkout(
    payload: CheckoutRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CheckoutResponse:
    if settings.payments_enabled:
        # Real payment integration lands in a later phase.
        raise HTTPException(status_code=501, detail="Payments not implemented yet.")

    email = payload.email.lower()
    source = f"waitlist:{payload.product}"
    lead = db.scalar(select(Lead).where(Lead.email == email))
    if lead is None:
        db.add(Lead(email=email, source=source))
    else:
        lead.source = source
    db.commit()

    return CheckoutResponse(
        status="waitlisted",
        message=(
            f"Checkout isn't open yet — you're on the waitlist for "
            f"{PRODUCT_LABELS[payload.product]}. We'll email you first."
        ),
    )
