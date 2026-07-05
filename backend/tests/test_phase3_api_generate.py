"""Phase 3 API: /api/generate + /api/episodes + status, offline (PRD 6, 11.5).

The generation runner is overridden with a stub that runs the orchestrator
synchronously against the test DB using fake clients — so a POST returns 202 and
the episode reaches READY within the test, no credits, no real background loop.
"""

import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.deps import get_current_user, get_generation_runner  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import Length, Preference, User
from app.services.generation.orchestrator import generate_episode
from tests.fakes import FakeLLMClient, make_fake_news_service


async def _make_ctx(*, noop_runner: bool = False):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with maker() as s:
        u = User(name="Sam", email="sam@x.com")
        s.add(u)
        await s.flush()
        s.add(Preference(user_id=u.id, interests=["tech"], podcast_length=Length.SHORT))
        await s.commit()

    async def _get_db():
        async with maker() as session:
            yield session

    async def _fake_runner(episode_id: int) -> None:
        async with maker() as session:
            await generate_episode(
                session, episode_id,
                llm_client=FakeLLMClient(),
                news_service=make_fake_news_service(2),
                audio_hook=None,
            )

    async def _noop_runner(episode_id: int) -> None:
        pass  # leaves the episode pending (simulates a still-running pipeline)

    app = create_app()
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_generation_runner] = (
        (lambda: _noop_runner) if noop_runner else (lambda: _fake_runner)
    )
    return app, engine


@pytest_asyncio.fixture
async def app_ctx():
    app, engine = await _make_ctx()
    with TestClient(app) as c:
        yield c
    await engine.dispose()


@pytest_asyncio.fixture
async def app_ctx_pending():
    """Client whose runner never finishes — episodes stay pending."""
    app, engine = await _make_ctx(noop_runner=True)
    with TestClient(app) as c:
        yield c
    await engine.dispose()


def test_generate_returns_202_and_creates(app_ctx):
    resp = app_ctx.post("/api/generate")
    assert resp.status_code == 202
    body = resp.json()
    assert body["created"] is True
    assert body["status"] == "pending"
    episode_id = body["episode_id"]

    # BackgroundTasks ran the (synchronous) fake runner on response close.
    status = app_ctx.get(f"/api/episodes/{episode_id}/status").json()
    assert status["status"] == "ready"
    assert any(s["stage"] == "ai_pipeline" for s in status["stages"])

    detail = app_ctx.get(f"/api/episodes/{episode_id}").json()
    assert detail["script"]
    assert len(detail["stories"]) == 2


def test_generate_creates_new_episode_each_call(app_ctx):
    """Revision: multiple episodes per day — every call creates a new one."""
    first = app_ctx.post("/api/generate")
    second = app_ctx.post("/api/generate")
    assert first.status_code == 202
    assert second.status_code == 202
    b1, b2 = first.json(), second.json()
    assert b1["created"] is True and b2["created"] is True
    assert b1["episode_id"] != b2["episode_id"]  # distinct episodes

    # Both exist independently, each with its own clean set of stories.
    d1 = app_ctx.get(f"/api/episodes/{b1['episode_id']}").json()
    d2 = app_ctx.get(f"/api/episodes/{b2['episode_id']}").json()
    assert len(d1["stories"]) == 2
    assert len(d2["stories"]) == 2


def test_generate_ignores_force_param(app_ctx):
    """The legacy force query param is undeclared and simply ignored."""
    r = app_ctx.post("/api/generate?force=true")
    assert r.status_code == 202
    assert r.json()["created"] is True


def test_generate_409_while_in_flight(app_ctx_pending):
    """A second generate is rejected while one is still pending/generating."""
    first = app_ctx_pending.post("/api/generate")
    assert first.status_code == 202

    second = app_ctx_pending.post("/api/generate")
    assert second.status_code == 409
    assert "already being generated" in second.json()["error"]["message"]


def test_list_episodes(app_ctx):
    app_ctx.post("/api/generate")
    rows = app_ctx.get("/api/episodes").json()
    assert len(rows) == 1
    assert rows[0]["status"] == "ready"


def test_episode_not_found_404(app_ctx):
    assert app_ctx.get("/api/episodes/999").status_code == 404
    assert app_ctx.get("/api/episodes/999/status").status_code == 404
