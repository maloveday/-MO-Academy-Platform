"""Signup funnel: capture, double-opt-in, primer delivery."""

from sqlalchemy import select

from app.models import Lead
from tests.conftest import ClientBundle


def _confirm_link(body: str) -> str:
    for token in body.split():
        if token.startswith("http") and "confirm?token=" in token:
            return token
    raise AssertionError(f"no confirmation link in email body:\n{body}")


def test_signup_stores_lead_and_sends_confirmation(client: ClientBundle) -> None:
    res = client.http.post(
        "/api/signup", json={"email": "Ada@Example.com", "source": "landing:primer"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "pending"

    with client.session_factory() as db:
        lead = db.scalar(select(Lead))
        assert lead is not None
        assert lead.email == "ada@example.com"  # normalised
        assert lead.source == "landing:primer"
        assert not lead.is_confirmed

    assert len(client.outbox) == 1
    assert client.outbox[0].to == "ada@example.com"
    assert "confirm" in client.outbox[0].subject.lower()


def test_confirm_marks_lead_and_sends_primer(client: ClientBundle) -> None:
    client.http.post("/api/signup", json={"email": "ada@example.com"})
    link = _confirm_link(client.outbox[0].body)

    res = client.http.get(link)
    assert res.status_code == 200
    assert "confirmed" in res.text.lower()

    with client.session_factory() as db:
        lead = db.scalar(select(Lead))
        assert lead.is_confirmed
        assert lead.primer_sent_at is not None

    primer = client.outbox[1]
    assert primer.to == "ada@example.com"
    assert "MO in 30 Minutes" in primer.subject
    assert "interaction patterns" in primer.body


def test_confirm_is_idempotent_and_primer_sent_once(client: ClientBundle) -> None:
    client.http.post("/api/signup", json={"email": "ada@example.com"})
    link = _confirm_link(client.outbox[0].body)

    assert client.http.get(link).status_code == 200
    assert client.http.get(link).status_code == 200
    # 1 confirmation + exactly 1 primer despite the double click.
    assert len(client.outbox) == 2


def test_confirm_rejects_bad_token(client: ClientBundle) -> None:
    res = client.http.get("/api/signup/confirm?token=not-a-real-token")
    assert res.status_code == 404


def test_duplicate_signup_resends_confirmation_with_new_token(
    client: ClientBundle,
) -> None:
    client.http.post("/api/signup", json={"email": "ada@example.com"})
    client.http.post("/api/signup", json={"email": "ada@example.com"})

    assert len(client.outbox) == 2
    first = _confirm_link(client.outbox[0].body)
    second = _confirm_link(client.outbox[1].body)
    assert first != second  # token rotated
    # Old link is dead, new one works.
    assert client.http.get(first).status_code == 404
    assert client.http.get(second).status_code == 200

    with client.session_factory() as db:
        assert len(db.scalars(select(Lead)).all()) == 1


def test_signup_after_confirmation_is_idempotent(client: ClientBundle) -> None:
    client.http.post("/api/signup", json={"email": "ada@example.com"})
    client.http.get(_confirm_link(client.outbox[0].body))

    res = client.http.post("/api/signup", json={"email": "ada@example.com"})
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert len(client.outbox) == 2  # no extra emails


def test_signup_rejects_invalid_email(client: ClientBundle) -> None:
    res = client.http.post("/api/signup", json={"email": "not-an-email"})
    assert res.status_code == 422
    assert client.outbox == []
