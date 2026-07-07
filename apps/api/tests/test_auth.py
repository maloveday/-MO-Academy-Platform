"""Magic-link auth: request, verify, sessions, expiry, logout."""

from datetime import timedelta

from sqlalchemy import select

from app.models import MagicLinkToken, User, utcnow
from tests.conftest import ClientBundle, login


def _magic_link(bundle: ClientBundle) -> str:
    return next(
        word
        for word in bundle.outbox[-1].body.split()
        if word.startswith("http") and "verify?token=" in word
    )


def test_request_link_creates_user_and_sends_email(client: ClientBundle) -> None:
    res = client.http.post(
        "/api/auth/request-link", json={"email": "Student@Example.com"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "sent"

    with client.session_factory() as db:
        user = db.scalar(select(User))
        assert user is not None
        assert user.email == "student@example.com"
        assert user.last_login_at is None

    assert len(client.outbox) == 1
    assert "sign-in" in client.outbox[0].subject.lower()
    assert "verify?token=" in client.outbox[0].body


def test_verify_sets_session_cookie(client: ClientBundle) -> None:
    client.http.post("/api/auth/request-link", json={"email": "s@example.com"})
    res = client.http.get(_magic_link(client), follow_redirects=False)

    assert res.status_code == 303
    assert res.headers["location"] == "/dashboard.html"
    assert "mo_session=" in res.headers.get("set-cookie", "")

    me = client.http.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "s@example.com"

    with client.session_factory() as db:
        assert db.scalar(select(User)).last_login_at is not None


def test_magic_link_is_single_use(client: ClientBundle) -> None:
    client.http.post("/api/auth/request-link", json={"email": "s@example.com"})
    link = _magic_link(client)
    assert client.http.get(link, follow_redirects=False).status_code == 303
    assert client.http.get(link, follow_redirects=False).status_code == 400


def test_expired_magic_link_rejected(client: ClientBundle) -> None:
    client.http.post("/api/auth/request-link", json={"email": "s@example.com"})
    with client.session_factory() as db:
        token = db.scalar(select(MagicLinkToken))
        token.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()
    assert (
        client.http.get(_magic_link(client), follow_redirects=False).status_code
        == 400
    )


def test_invalid_token_rejected(client: ClientBundle) -> None:
    res = client.http.get(
        "/api/auth/verify?token=bogus-token", follow_redirects=False
    )
    assert res.status_code == 400


def test_me_requires_session(client: ClientBundle) -> None:
    assert client.http.get("/api/auth/me").status_code == 401


def test_logout_ends_session(client: ClientBundle) -> None:
    login(client)
    assert client.http.get("/api/auth/me").status_code == 200

    assert client.http.post("/api/auth/logout").status_code == 200
    assert client.http.get("/api/auth/me").status_code == 401


def test_repeat_login_reuses_user(client: ClientBundle) -> None:
    login(client, "s@example.com")
    client.http.cookies.clear()
    login(client, "s@example.com")
    with client.session_factory() as db:
        assert len(db.scalars(select(User)).all()) == 1
