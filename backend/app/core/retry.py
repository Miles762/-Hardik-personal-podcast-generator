"""Exponential-backoff retry for flaky external calls (PRD 11.1).

A small async helper used by the OpenAI, ElevenLabs, and news provider clients.
Delay is injectable so tests run instantly (no real sleeping).

Retry policy: only *transient* failures are retried (network errors, timeouts,
and HTTP 429/5xx). Everything else — a bug, bad input, an auth error, a 4xx —
propagates immediately instead of being retried, so real errors surface clearly
rather than being masked as "failed after N attempts". Callers that need a
broader policy (e.g. the AI client, which also retries a malformed model
response) pass an explicit ``retry_on`` tuple.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

# HTTP status codes worth retrying (transient server / throttling responses).
RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})

# Exception types that represent a transient failure worth retrying.
TRANSIENT_EXCEPTIONS: tuple[type[BaseException], ...] = (
    httpx.TransportError,   # connect/read/write/pool errors, timeouts
    ConnectionError,
    TimeoutError,
)


def is_transient(exc: BaseException) -> bool:
    """True if ``exc`` is a transient failure that a retry might fix."""
    if isinstance(exc, TRANSIENT_EXCEPTIONS):
        return True
    # A 429/5xx HTTP response is transient; a 4xx (bad request/auth) is not.
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS
    return False


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    max_retries: int | None = None,
    base_delay: float | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    label: str = "call",
    retry_on: Callable[[BaseException], bool] = is_transient,
) -> T:
    """Call ``fn`` with exponential backoff on transient failures.

    ``retry_on`` decides whether a given exception is worth retrying; the default
    retries only transient network/HTTP failures. A non-retryable exception is
    re-raised immediately so real bugs are not silently retried.
    """
    settings = get_settings()
    attempts = max_retries if max_retries is not None else settings.max_retries
    delay = base_delay if base_delay is not None else settings.retry_base_delay_sec

    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return await fn()
        except Exception as exc:
            if not retry_on(exc):
                raise  # non-transient: surface the real error immediately
            last_exc = exc
            if attempt == attempts - 1:
                break
            wait = delay * (2**attempt)
            logger.warning(
                "%s failed (attempt %d/%d): %s; retrying in %.2fs",
                label, attempt + 1, attempts, exc, wait,
            )
            await sleep(wait)
    assert last_exc is not None
    raise last_exc
