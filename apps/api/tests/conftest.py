"""Test fixtures: in-memory-style SQLite DB, captured outgoing email."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

# Configure the environment before app modules import settings.
os.environ["ADMIN_TOKEN"] = "test-admin-token"
os.environ["EMAIL_BACKEND"] = "console"
os.environ["PAYMENTS_ENABLED"] = "false"
os.environ["BASE_URL"] = "http://testserver"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator["ClientBundle"]:
    """A TestClient wired to a fresh SQLite file DB and a recording emailer."""
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app import db as app_db
    from app.db import Base, get_db
    from app.emailer import EmailMessage, get_email_backend
    from app.main import create_app

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.sqlite3'}",
        connect_args={"check_same_thread": False},
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(app_db, "engine", engine)
    monkeypatch.setattr(app_db, "SessionLocal", TestingSession)

    outbox: list[EmailMessage] = []

    class RecordingEmailBackend:
        def send(self, message: EmailMessage) -> None:
            outbox.append(message)

    def override_get_db() -> Iterator:
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_backend] = RecordingEmailBackend

    with TestClient(app) as test_client:
        yield ClientBundle(test_client, outbox, TestingSession)

    engine.dispose()


class ClientBundle:
    """The TestClient plus the email outbox and a session factory for asserts."""

    def __init__(self, http, outbox, session_factory) -> None:
        self.http = http
        self.outbox = outbox
        self.session_factory = session_factory


@pytest.fixture()
def seeded_client(client: ClientBundle) -> ClientBundle:
    """Client with the curriculum seeded from the real syllabus file."""
    from app.config import get_settings
    from app.seed import seed

    with client.session_factory() as db:
        seed(db, get_settings().content_dir / "syllabus_full.md")
    return client


def login(bundle: ClientBundle, email: str = "student@example.com") -> None:
    """Drive the magic-link flow; leaves the session cookie on the client."""
    res = bundle.http.post("/api/auth/request-link", json={"email": email})
    assert res.status_code == 200
    link = next(
        word
        for word in bundle.outbox[-1].body.split()
        if word.startswith("http") and "verify?token=" in word
    )
    res = bundle.http.get(link, follow_redirects=False)
    assert res.status_code == 303, res.text
