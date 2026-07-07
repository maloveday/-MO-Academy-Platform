"""Checkout stub: waitlist fallback while PAYMENTS_ENABLED=false."""

from sqlalchemy import select

from app.models import Lead
from tests.conftest import ClientBundle


def test_checkout_waitlists_when_payments_disabled(client: ClientBundle) -> None:
    res = client.http.post(
        "/api/checkout", json={"email": "buyer@example.com", "product": "cohort"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "waitlisted"
    assert "waitlist" in body["message"]

    with client.session_factory() as db:
        lead = db.scalar(select(Lead))
        assert lead.email == "buyer@example.com"
        assert lead.source == "waitlist:cohort"


def test_checkout_updates_existing_lead_source(client: ClientBundle) -> None:
    client.http.post("/api/signup", json={"email": "buyer@example.com"})
    client.http.post(
        "/api/checkout", json={"email": "buyer@example.com", "product": "self_paced"}
    )
    with client.session_factory() as db:
        leads = db.scalars(select(Lead)).all()
        assert len(leads) == 1
        assert leads[0].source == "waitlist:self_paced"


def test_checkout_rejects_unknown_product(client: ClientBundle) -> None:
    res = client.http.post(
        "/api/checkout", json={"email": "buyer@example.com", "product": "yacht"}
    )
    assert res.status_code == 422
