"""FastAPI application: API under /api, static marketing site at /."""

import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import admin, auth, checkout, course, labs, signup

logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="MO Academy", version="0.1.0")

    app.include_router(signup.router)
    app.include_router(checkout.router)
    app.include_router(admin.router)
    app.include_router(auth.router)
    app.include_router(course.router)
    app.include_router(labs.router)

    @app.get("/api/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # Mounted last so /api/* wins; html=True serves index.html at /.
    app.mount(
        "/", StaticFiles(directory=settings.web_dir, html=True), name="web"
    )
    return app


app = create_app()
