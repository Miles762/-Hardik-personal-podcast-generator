"""Phase 8: the headless sample script runs end-to-end with mocks (no credits).

Proves scripts.make_sample wires news -> AI -> audio -> stored file and writes
sample.mp3, using fakes so the test spends zero API credits (PRD 11.5).
"""

import os

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.db.base import Base

os.environ.setdefault("ENABLE_SCHEDULER", "false")


@pytest_asyncio.fixture
async def wired(monkeypatch, tmp_path):
    # Set fake keys before anything reads settings.
    from app.core.config import get_settings

    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test")
    get_settings.cache_clear()

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    import scripts.make_sample as ms
    from tests.fakes import FakeLLMClient, make_fake_news_service

    # Point the script at the in-memory DB + fake clients + a temp audio dir.
    monkeypatch.setattr(ms, "SessionLocal", maker)
    monkeypatch.setattr(ms, "build_llm_client", lambda: FakeLLMClient())
    monkeypatch.setattr(ms, "NewsService", lambda: make_fake_news_service(3))

    audio_dir = tmp_path / "audio"

    def _fake_hook_builder(session):  # sync, like the real build_audio_hook
        async def _hook(episode, script):
            audio_dir.mkdir(parents=True, exist_ok=True)
            (audio_dir / f"episode_{episode.id}.mp3").write_bytes(b"ID3fake")
            return f"/audio/episode_{episode.id}.mp3", 42

        return _hook

    monkeypatch.setattr(ms, "build_audio_hook", _fake_hook_builder)
    monkeypatch.setattr(ms, "AUDIO_DIR", audio_dir)
    monkeypatch.setattr(ms, "SAMPLE_OUT", tmp_path / "out")

    yield ms, tmp_path
    await engine.dispose()


async def test_make_sample_produces_mp3(wired):
    ms, tmp_path = wired
    from app.models import Length, Voice

    await ms.run(["space", "tech"], Length.SHORT, Voice.RACHEL)

    out = tmp_path / "out" / "sample.mp3"
    assert out.exists()
    assert out.read_bytes() == b"ID3fake"


async def test_make_sample_is_rerunnable(wired):
    """Running twice resets the sample episode in place (no accumulation)."""
    ms, tmp_path = wired
    from app.models import Length, Voice

    await ms.run(["space"], Length.SHORT, Voice.RACHEL)
    await ms.run(["space"], Length.SHORT, Voice.RACHEL)

    async with ms.SessionLocal() as session:
        from sqlalchemy import func, select

        from app.models import Episode, Story

        episodes = (await session.execute(select(func.count()).select_from(Episode))).scalar_one()
        stories = (await session.execute(select(func.count()).select_from(Story))).scalar_one()
    assert episodes == 1      # same sample row reused
    assert stories == 3       # not 6
