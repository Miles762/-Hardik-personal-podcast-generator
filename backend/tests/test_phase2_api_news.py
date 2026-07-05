"""Phase 2 API test: GET /api/news end-to-end, offline (PRD 11.5).

Uses a fresh in-memory DB with a seeded user + a NewsService wired to fake
providers, so the full router → service → rank → serialize path runs with no
network and no credits.
"""

from datetime import UTC, datetime

import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.deps import get_news_service
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import Length, Preference, User
from app.schemas.news import Article
from app.services.news.cache import TTLCache
from app.services.news.service import NewsService


class _FakeProvider:
    def __init__(self, name, articles):
        self.name = name
        self._articles = articles

    async def fetch(self):
        return self._articles


def _article(title, source, url, content="", popularity=0.0):
    return Article(
        title=title, source=source, url=url,
        published_at=datetime.now(UTC),
        content=content, popularity=popularity,
    )


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with maker() as s:
        user = User(name="Demo", email="demo@x.com")
        s.add(user)
        await s.flush()
        s.add(Preference(user_id=user.id, interests=["space", "mars"],
                         podcast_length=Length.SHORT))
        await s.commit()

    async def _get_db():
        async with maker() as session:
            yield session

    # Fake providers: enrichment disabled by using content already present and
    # a cache; we also disable network extraction by monkeypatching per test.
    articles = [
        _article("NASA Mars mission update", "NASA", "https://n.com/mars",
                 content="space mars rover", popularity=10),
        _article("Stock market wobbles", "Reuters", "https://r.com/mkt",
                 content="finance markets", popularity=5),
    ]
    service = NewsService(
        providers=[_FakeProvider("nasa", articles)],
        cache=TTLCache(),
    )

    app = create_app()
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_news_service] = lambda: service

    with TestClient(app) as c:
        yield c, service
    await engine.dispose()


def test_news_happy_path_ranked(client, monkeypatch):
    c, _ = client
    # Skip network extraction; return articles unchanged.
    from app.services.news import service as service_mod

    async def _no_enrich(arts, **kw):
        return arts

    monkeypatch.setattr(service_mod, "enrich_top_n", _no_enrich)

    resp = c.get("/api/news")
    assert resp.status_code == 200
    body = resp.json()
    assert body["cached"] is False
    assert len(body["items"]) >= 1
    # Space-interest article should outrank the finance one.
    assert body["items"][0]["title"] == "NASA Mars mission update"
    assert body["items"][0]["score"] >= body["items"][-1]["score"]


def test_news_second_call_is_cached(client, monkeypatch):
    c, _ = client
    from app.services.news import service as service_mod

    async def _no_enrich(arts, **kw):
        return arts

    monkeypatch.setattr(service_mod, "enrich_top_n", _no_enrich)

    first = c.get("/api/news").json()
    second = c.get("/api/news").json()
    assert first["cached"] is False
    assert second["cached"] is True
