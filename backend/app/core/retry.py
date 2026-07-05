"""Exponential-backoff retry for flaky external calls (PRD 11.1).

A small async helper used by the OpenAI, ElevenLabs, and provider clients. Delay
is injectable so tests run instantly (no real sleeping).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    max_retries: int | None = None,
    base_delay: float | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    label: str = "call",
) -> T:
    """Call ``fn`` with exponential backoff. Re-raises the last error on exhaustion."""
    settings = get_settings()
    attempts = max_retries if max_retries is not None else settings.max_retries
    delay = base_delay if base_delay is not None else settings.retry_base_delay_sec

    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return await fn()
        except Exception as exc:  # noqa: BLE001 — retry any transient failure
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
