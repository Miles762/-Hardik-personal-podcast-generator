"""In-process rate limiter for the generate endpoint (PRD 11.3).

Sliding-window counter keyed by client. Sufficient for the single-node take-home;
a real deployment would use Redis. Time source is injectable for tests.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


class RateLimiter:
    def __init__(self, *, time_fn: Callable[[], float] = time.monotonic) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._now = time_fn

    def check(self, key: str, limit: int, window_sec: int) -> bool:
        now = self._now()
        q = self._hits[key]
        while q and now - q[0] > window_sec:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


_limiter = RateLimiter()


async def rate_limit_generate(request: Request) -> None:
    """FastAPI dependency: 429 when the client exceeds the generate limit."""
    settings = get_settings()
    key = request.client.host if request.client else "anonymous"
    if not _limiter.check(
        key, settings.generate_rate_limit, settings.generate_rate_window_sec
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again shortly.",
        )
