"""Structured JSON logging + request-id middleware (PRD 11.6).

structlog renders one JSON line per event with a request id, path, method, status,
and duration. The pipeline logs stage/timing/token counts through the same logger,
so operational tiles and traces share a format.
"""

from __future__ import annotations

import logging
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp


def configure_logging() -> None:
    # Route stdlib logging (uvicorn, apscheduler, our services' getLogger calls)
    # to stdout at INFO so scheduler/pipeline activity is observable (PRD 11.6).
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach a request id and log each request's method/path/status/duration."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            request_id=request_id,
        )
        response.headers["x-request-id"] = request_id
        return response
