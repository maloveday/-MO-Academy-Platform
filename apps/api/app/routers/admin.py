"""Admin-only endpoints, guarded by the X-Admin-Token header."""

import csv
import io
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models import Lead

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(
    settings: Annotated[Settings, Depends(get_settings)],
    x_admin_token: Annotated[str, Header()] = "",
) -> None:
    if not settings.admin_token or not secrets.compare_digest(
        x_admin_token, settings.admin_token
    ):
        raise HTTPException(status_code=403, detail="Admin token required.")


@router.get(
    "/leads.csv",
    response_class=PlainTextResponse,
    dependencies=[Depends(require_admin)],
)
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
