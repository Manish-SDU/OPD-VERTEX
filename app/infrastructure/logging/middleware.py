"""FastAPI middleware for HTTP request/response logging.

This middleware acts as an around-advice aspect for the entire request
lifecycle — capturing method, path, status, duration, and client IP
without any modifications to route handlers.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("opd_vertex.middleware.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every HTTP request and response with timing information."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()

        # Safe client IP extraction
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        logger.info("[REQUEST]  %s %s from %s", method, path, client_ip)

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "[REQUEST]  %s %s from %s — unhandled error after %.1fms",
                method,
                path,
                client_ip,
                elapsed_ms,
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "[RESPONSE] %s %s → %s (%.1fms)",
            method,
            path,
            response.status_code,
            elapsed_ms,
        )
        return response
