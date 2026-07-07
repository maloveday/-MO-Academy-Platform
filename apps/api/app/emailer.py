"""Pluggable email delivery: console (dev) or SMTP."""

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage
from typing import Protocol

from app.config import Settings, get_settings

logger = logging.getLogger("mo_academy.email")


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str


class EmailBackend(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class ConsoleEmailBackend:
    """Logs emails to stdout instead of sending — the dev default."""

    def send(self, message: EmailMessage) -> None:
        logger.info(
            "\n--- EMAIL (console backend) ---\nTo: %s\nSubject: %s\n\n%s\n--- END EMAIL ---",
            message.to,
            message.subject,
            message.body,
        )


class SMTPEmailBackend:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, message: EmailMessage) -> None:
        s = self._settings
        mime = MimeMessage()
        mime["From"] = s.email_from
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.body)

        with smtplib.SMTP(s.smtp_host, s.smtp_port) as client:
            if s.smtp_starttls:
                client.starttls()
            if s.smtp_username:
                client.login(s.smtp_username, s.smtp_password)
            client.send_message(mime)


def get_email_backend() -> EmailBackend:
    """FastAPI dependency; override in tests to capture outgoing mail."""
    settings = get_settings()
    if settings.email_backend == "smtp":
        return SMTPEmailBackend(settings)
    return ConsoleEmailBackend()
