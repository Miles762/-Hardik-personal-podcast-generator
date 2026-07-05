"""In-memory TTL cache for merged news results (PRD 7).

A tiny interface (`get`/`set`) so a Redis-backed implementation can replace it
without touching callers. TTL default 1 hour. Time source is injectable for
deterministic tests.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

DEFAULT_TTL_SECONDS = 3600  # 1 hour (PRD 7)


@dataclass
class _Entry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    """Single-value-per-key in-memory cache with per-entry expiry."""

    def __init__(
        self,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        *,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds
        self._now = time_fn
        self._store: dict[str, _Entry[T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if self._now() >= entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        self._store[key] = _Entry(value=value, expires_at=self._now() + self._ttl)

    def clear(self) -> None:
        self._store.clear()
