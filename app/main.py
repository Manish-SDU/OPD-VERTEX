"""FastAPI entrypoint for OPD-Vertex scaffold."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import router
from app.core.config import get_settings
from app.core.constants import APP_VERSION
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name, version=APP_VERSION, debug=settings.debug)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(router)
