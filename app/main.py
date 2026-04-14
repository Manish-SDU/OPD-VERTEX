"""FastAPI entrypoint for OPD-Vertex scaffold."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import router
from app.core.config import get_settings
from app.core.constants import APP_VERSION
from app.core.logging import configure_logging
from app.infrastructure.bootstrap.startup import StartupBootstrapper
from app.infrastructure.logging.middleware import RequestLoggingMiddleware

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI):
    StartupBootstrapper(settings).run()
    yield


app = FastAPI(
    title=settings.app_name,
    version=APP_VERSION,
    debug=settings.debug,
    lifespan=lifespan,
)
app.add_middleware(RequestLoggingMiddleware)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(router)
