"""Phase 7 API: JSON error envelope + rate limiting (PRD 6, 11.3). Offline."""

import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.config import get_settings
from app.core.deps import get_generation_runner
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import Length, Preference, User


@pytest_asyncio.fixture
async def client():
    get_settings.cache_clear()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with maker() as s:
        u = User(name="Sam", email="s@x.com")
        s.add(u)
        await s.flush()
        s.add(Preference(user_id=u.id, interests=["tech"], podcast_length=Length.SHORT))
        await s.commit()

    async def _get_db():
        async with maker() as session:
            yield session

    async def _noop_runner(episode_id: int):
        pass

    app = create_app()
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_generation_runner] = lambda: _noop_runner
    with TestClient(app) as c:
        yield c
    await engine.dispose()


def test_error_envelope_on_404(client):
    body = client.get("/api/episodes/999").json()
    assert "error" in body
    assert body["error"]["code"] == 404
    assert "message" in body["error"]


def test_error_envelope_on_validation(client):
    body = client.patch("/api/preferences", json={"voice": "bad"}).json()
    assert body["error"]["code"] == 422


def test_request_id_header_present(client):
    resp = client.get("/api/health")
    assert "x-request-id" in resp.headers


def test_generate_rate_limited(client, monkeypatch):
    # Tighten the limit for the test.
    s = get_settings()
    monkeypatch.setattr(s, "generate_rate_limit", 2)
    monkeypatch.setattr(s, "generate_rate_window_sec", 60)
    # Reset the module limiter so counts start fresh.
    import app.core.ratelimit as rl_mod
    monkeypatch.setattr(rl_mod, "_limiter", rl_mod.RateLimiter())

    codes = [client.post("/api/generate").status_code for _ in range(3)]
    assert codes[0] in (200, 202)
    assert 429 in codes  # the 3rd exceeds the limit
