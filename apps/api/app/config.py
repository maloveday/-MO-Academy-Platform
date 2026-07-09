"""Application settings, loaded from environment / .env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    base_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./mo_academy.sqlite3"

    email_backend: Literal["console", "smtp"] = "console"
    email_from: str = "MO Academy <hello@example.com>"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True

    admin_token: str = ""
    payments_enabled: bool = False
    # Set true in production (HTTPS) so session cookies are Secure.
    cookie_secure: bool = False

    web_dir: Path = REPO_ROOT / "apps" / "web"
    content_dir: Path = REPO_ROOT / "content"
    labs_dir: Path = REPO_ROOT / "labs"

    # "docker" runs submissions sandboxed (--network=none, mem/cpu limits) in
    # GRADER_IMAGE; "subprocess" runs them unsandboxed — dev/tests only.
    grader_mode: Literal["subprocess", "docker"] = "subprocess"
    grader_image: str = "mo-academy-grader"
    grader_timeout: int = 180


@lru_cache
def get_settings() -> Settings:
    return Settings()
