"""Phase 5 backend: GET/PATCH /api/preferences (PRD 6, 10). Offline."""

import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.deps import get_current_user  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import Length, Preference, User


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with maker() as s:
        u = User(name="Sam", email="sam@x.com")
        s.add(u)
        await s.flush()
        s.add(Preference(user_id=u.id, interests=["tech"], podcast_length=Length.MEDIUM))
        await s.commit()

    async def _get_db():
        async with maker() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    await engine.dispose()


def test_get_preferences(client):
    body = client.get("/api/preferences").json()
    assert body["name"] == "Sam"
    assert body["interests"] == ["tech"]
    assert body["podcast_length"] == "medium"


def test_patch_updates_fields(client):
    resp = client.patch("/api/preferences", json={
        "name": "Alex", "interests": ["space", "ai"],
        "voice": "adam", "tone": "witty",
        "podcast_length": "long", "schedule": "8:5",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Alex"
    assert body["interests"] == ["space", "ai"]
    assert body["voice"] == "adam"
    assert body["schedule"] == "08:05"     # normalized


def test_patch_rejects_unknown_field(client):
    resp = client.patch("/api/preferences", json={"nope": 1})
    assert resp.status_code == 422


def test_patch_rejects_bad_schedule(client):
    resp = client.patch("/api/preferences", json={"schedule": "25:00"})
    assert resp.status_code == 422


def test_patch_rejects_bad_enum(client):
    resp = client.patch("/api/preferences", json={"voice": "not-a-voice"})
    assert resp.status_code == 422


def test_patch_rejects_whitespace_only_name(client):
    # Regression: " " passed min_length=1 and rendered as "Hey  ".
    resp = client.patch("/api/preferences", json={"name": "   "})
    assert resp.status_code == 422


def test_patch_collapses_name_whitespace(client):
    resp = client.patch("/api/preferences", json={"name": "  Alex   Chen  "})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Alex Chen"


def test_patch_dedupes_and_trims_interests(client):
    resp = client.patch(
        "/api/preferences",
        json={"interests": ["  AI ", "ai", "Ai", "space   news", "", "   "]},
    )
    assert resp.status_code == 200
    # First-seen casing wins; whitespace collapsed; empties dropped.
    assert resp.json()["interests"] == ["AI", "space news"]


def test_patch_rejects_overlong_interest(client):
    resp = client.patch("/api/preferences", json={"interests": ["x" * 101]})
    assert resp.status_code == 422


def test_patch_rejects_too_many_interests(client):
    resp = client.patch(
        "/api/preferences", json={"interests": [f"topic {i}" for i in range(21)]}
    )
    assert resp.status_code == 422
