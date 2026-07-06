"""Phase 7: retry backoff, rate limiter, scheduler registration, error envelope.

All offline/deterministic (PRD 11.1, 11.3, 4.3, 6). No real sleeping, no network.
"""

import httpx
import pytest

from app.core.ratelimit import RateLimiter
from app.core.retry import is_transient, with_retry

# ---- Retry with exponential backoff (PRD 11.1) ----

async def test_retry_succeeds_after_transient_failures() -> None:
    calls = {"n": 0}
    sleeps: list[float] = []

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise httpx.ConnectError("transient network blip")
        return "ok"

    async def fake_sleep(d):
        sleeps.append(d)

    result = await with_retry(flaky, max_retries=5, base_delay=0.5, sleep=fake_sleep)
    assert result == "ok"
    assert calls["n"] == 3
    assert sleeps == [0.5, 1.0]  # exponential: 0.5*2^0, 0.5*2^1


async def test_retry_reraises_transient_after_exhaustion() -> None:
    async def always_fail():
        raise httpx.ConnectError("still down")

    async def fake_sleep(d):
        pass

    with pytest.raises(httpx.ConnectError, match="still down"):
        await with_retry(always_fail, max_retries=3, base_delay=0.1, sleep=fake_sleep)


async def test_retry_does_not_retry_non_transient_errors() -> None:
    """A real bug (e.g. ValueError) must surface immediately, not be retried."""
    calls = {"n": 0}

    async def buggy():
        calls["n"] += 1
        raise ValueError("this is a real bug, not a network blip")

    async def fake_sleep(d):
        raise AssertionError("should not sleep/retry a non-transient error")

    with pytest.raises(ValueError, match="real bug"):
        await with_retry(buggy, max_retries=5, base_delay=0.1, sleep=fake_sleep)
    assert calls["n"] == 1  # called exactly once, no retries


def test_is_transient_classifies_correctly() -> None:
    assert is_transient(httpx.ConnectError("x")) is True
    assert is_transient(TimeoutError()) is True
    # 429 / 5xx are transient; 400 / 401 are not.
    resp429 = httpx.Response(429, request=httpx.Request("GET", "http://x"))
    resp400 = httpx.Response(400, request=httpx.Request("GET", "http://x"))
    assert is_transient(httpx.HTTPStatusError("x", request=resp429.request, response=resp429)) is True
    assert is_transient(httpx.HTTPStatusError("x", request=resp400.request, response=resp400)) is False
    assert is_transient(ValueError("bug")) is False


# ---- Rate limiter (PRD 11.3) ----

def test_rate_limiter_allows_under_limit_then_blocks() -> None:
    clock = {"t": 0.0}
    rl = RateLimiter(time_fn=lambda: clock["t"])
    assert all(rl.check("ip", limit=3, window_sec=60) for _ in range(3))
    assert rl.check("ip", limit=3, window_sec=60) is False  # 4th blocked


def test_rate_limiter_window_slides() -> None:
    clock = {"t": 0.0}
    rl = RateLimiter(time_fn=lambda: clock["t"])
    for _ in range(3):
        rl.check("ip", limit=3, window_sec=10)
    assert rl.check("ip", limit=3, window_sec=10) is False
    clock["t"] = 11.0  # window passed
    assert rl.check("ip", limit=3, window_sec=10) is True


def test_rate_limiter_isolates_keys() -> None:
    rl = RateLimiter(time_fn=lambda: 0.0)
    assert rl.check("a", 1, 60) is True
    assert rl.check("a", 1, 60) is False
    assert rl.check("b", 1, 60) is True  # different key unaffected


# ---- Scheduler registration (PRD 4.3) ----

def test_register_and_remove_user_job(monkeypatch) -> None:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    import app.services.scheduler.scheduler as sched_mod

    sched = AsyncIOScheduler(timezone="UTC")
    monkeypatch.setattr(sched_mod, "_scheduler", sched)

    sched_mod.register_user_job(1, "07:30")
    job = sched.get_job("generate-user-1")
    assert job is not None

    # Re-register with None removes the job (schedule turned off).
    sched_mod.register_user_job(1, None)
    assert sched.get_job("generate-user-1") is None
