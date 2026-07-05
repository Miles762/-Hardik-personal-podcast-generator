"""Phase 7: retry backoff, rate limiter, scheduler registration, error envelope.

All offline/deterministic (PRD 11.1, 11.3, 4.3, 6). No real sleeping, no network.
"""

import pytest

from app.core.ratelimit import RateLimiter
from app.core.retry import with_retry

# ---- Retry with exponential backoff (PRD 11.1) ----

async def test_retry_succeeds_after_transient_failures() -> None:
    calls = {"n": 0}
    sleeps: list[float] = []

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    async def fake_sleep(d):
        sleeps.append(d)

    result = await with_retry(flaky, max_retries=5, base_delay=0.5, sleep=fake_sleep)
    assert result == "ok"
    assert calls["n"] == 3
    assert sleeps == [0.5, 1.0]  # exponential: 0.5*2^0, 0.5*2^1


async def test_retry_reraises_after_exhaustion() -> None:
    async def always_fail():
        raise ValueError("nope")

    async def fake_sleep(d):
        pass

    with pytest.raises(ValueError, match="nope"):
        await with_retry(always_fail, max_retries=3, base_delay=0.1, sleep=fake_sleep)


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
