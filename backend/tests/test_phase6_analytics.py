"""Phase 6: analytics aggregation + /dashboard + /progress (PRD 10, 11.6). Offline."""

from datetime import UTC, date, datetime

import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import (
    Episode,
    EpisodeStatus,
    GenerationJob,
    JobStatus,
    Length,
    PlayEvent,
    Preference,
    User,
)
from app.services.analytics.service import build_dashboard


async def _seed(session) -> Episode:
    u = User(name="Sam", email="s@x.com")
    session.add(u)
    await session.flush()
    session.add(Preference(user_id=u.id, interests=["tech", "space"],
                           podcast_length=Length.MEDIUM))
    ep = Episode(user_id=u.id, episode_date=date.today(),
                 status=EpisodeStatus.READY, duration_sec=100)
    session.add(ep)
    await session.flush()
    # Two jobs with tokens + chars + timing → drive cost + latency.
    t0 = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    t1 = datetime(2025, 1, 1, 0, 0, 10, tzinfo=UTC)
    session.add(GenerationJob(episode_id=ep.id, stage="ai_pipeline",
                              status=JobStatus.DONE, tokens=1_000_000,
                              started_at=t0, finished_at=t1))
    session.add(GenerationJob(episode_id=ep.id, stage="audio",
                              status=JobStatus.DONE, chars=1000,
                              started_at=t0, finished_at=t1))
    session.add(GenerationJob(episode_id=ep.id, stage="news",
                              status=JobStatus.FAILED, error="x"))
    # PlayEvent: listened to 80/100s.
    session.add(PlayEvent(episode_id=ep.id, position_sec=80))
    await session.commit()
    return ep


@pytest_asyncio.fixture
async def ctx():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with maker() as s:
        await _seed(s)

    async def _get_db():
        async with maker() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c, maker
    await engine.dispose()


async def test_no_cost_tiles(ctx):
    """Cost tiles were removed: without an input/output token split any
    single-rate figure understates real spend, so we show none."""
    _, maker = ctx
    async with maker() as session:
        d = await build_dashboard(session)
    labels = {t.label for t in d.operational}
    assert "OpenAI Cost" not in labels
    assert "ElevenLabs Cost" not in labels


async def test_latency_and_failed_jobs_real(ctx):
    _, maker = ctx
    async with maker() as session:
        d = await build_dashboard(session)
    lat = next(t for t in d.operational if t.label == "Avg Stage Latency")
    failed = next(t for t in d.operational if t.label == "Failed Jobs")
    assert lat.value == 10.0            # both timed jobs are 10s
    assert failed.value == 1.0


async def test_listening_metrics_from_playevents(ctx):
    _, maker = ctx
    async with maker() as session:
        d = await build_dashboard(session)
    listen = next(t for t in d.product if t.label == "Avg Listening Time")
    completion = next(t for t in d.product if t.label == "Completion Rate")
    assert listen.value == 80.0
    assert completion.value == 80.0     # 80/100


async def test_dashboard_endpoint_shape(ctx):
    c, _ = ctx
    body = c.get("/api/dashboard").json()
    assert {"product", "user", "operational", "top_interests", "voice_distribution"} <= body.keys()
    assert body["top_interests"][0]["name"] in {"tech", "space"}
    # Seeded concept removed: no trends, no source labels on tiles.
    assert "trends" not in body
    for section in ("product", "user", "operational"):
        for tile in body[section]:
            assert "source" not in tile


def test_progress_endpoint_records_event(ctx):
    c, _ = ctx
    r = c.post("/api/episodes/1/progress", json={"position_sec": 42})
    assert r.status_code == 204


def test_progress_rejects_negative(ctx):
    c, _ = ctx
    r = c.post("/api/episodes/1/progress", json={"position_sec": -1})
    assert r.status_code == 422


def test_progress_404_for_missing_episode(ctx):
    c, _ = ctx
    r = c.post("/api/episodes/999/progress", json={"position_sec": 5})
    assert r.status_code == 404
