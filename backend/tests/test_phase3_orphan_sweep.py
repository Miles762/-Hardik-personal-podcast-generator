"""Phase 3: startup orphan sweep (PRD 4.2, 11.1). Offline via in-memory DB."""

from datetime import UTC, date, datetime, timedelta

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.db.base import Base
from app.models import Episode, EpisodeStatus, User


@pytest_asyncio.fixture
async def maker(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    m = async_sessionmaker(bind=engine, expire_on_commit=False)
    # Point the runner's SessionLocal at this in-memory DB.
    import app.services.generation.runner as runner_mod

    monkeypatch.setattr(runner_mod, "SessionLocal", m)
    yield m
    await engine.dispose()


async def test_sweep_marks_stale_generating_as_failed(maker):
    from app.services.generation.runner import sweep_orphaned_episodes

    old = datetime.now(UTC) - timedelta(hours=1)
    async with maker() as s:
        u = User(name="A", email="a@x.com")
        s.add(u)
        await s.flush()
        stale = Episode(
            user_id=u.id, episode_date=date(2025, 1, 1),
            status=EpisodeStatus.GENERATING, created_at=old,
        )
        fresh = Episode(
            user_id=u.id, episode_date=date(2025, 1, 2),
            status=EpisodeStatus.GENERATING,
        )
        s.add_all([stale, fresh])
        await s.commit()
        stale_id, fresh_id = stale.id, fresh.id

    swept = await sweep_orphaned_episodes()
    assert swept == 1

    async with maker() as s:
        stale_row = (await s.execute(select(Episode).where(Episode.id == stale_id))).scalar_one()
        fresh_row = (await s.execute(select(Episode).where(Episode.id == fresh_id))).scalar_one()
        assert stale_row.status == EpisodeStatus.FAILED
        assert stale_row.error == "orphaned by restart"
        assert fresh_row.status == EpisodeStatus.GENERATING  # too recent to sweep
