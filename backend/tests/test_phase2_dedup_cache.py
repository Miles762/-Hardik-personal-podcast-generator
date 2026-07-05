"""Phase 2 unit tests: dedup + cache TTL (PRD 7, 11.5). Pure, deterministic."""

from datetime import UTC, datetime

from app.schemas.news import Article
from app.services.news.cache import TTLCache
from app.services.news.dedup import deduplicate, normalize_url, title_similarity


def _article(title: str, url: str) -> Article:
    return Article(
        title=title,
        source="X",
        url=url,
        published_at=datetime.now(UTC),
    )


def test_normalize_url_strips_noise() -> None:
    a = normalize_url("https://www.x.com/story/?utm=1#frag")
    b = normalize_url("http://x.com/story")
    assert a == b


def test_title_similarity_bounds() -> None:
    assert title_similarity("a b c", "a b c") == 1.0
    assert title_similarity("apple orange", "car truck") == 0.0


def test_dedup_removes_url_duplicates() -> None:
    items = [
        _article("Story One", "https://x.com/1"),
        _article("Different Title", "https://www.x.com/1/"),  # same URL normalized
    ]
    assert len(deduplicate(items)) == 1


def test_dedup_removes_near_duplicate_titles() -> None:
    items = [
        _article("NASA launches new Mars rover today", "https://a.com/1"),
        _article("NASA launches new Mars rover today!", "https://b.com/2"),
        _article("Completely unrelated headline here", "https://c.com/3"),
    ]
    kept = deduplicate(items)
    assert len(kept) == 2


def test_cache_hit_and_expiry() -> None:
    clock = {"t": 0.0}
    cache: TTLCache[str] = TTLCache(ttl_seconds=100, time_fn=lambda: clock["t"])
    cache.set("k", "v")
    assert cache.get("k") == "v"          # hit
    clock["t"] = 99.0
    assert cache.get("k") == "v"          # still valid
    clock["t"] = 101.0
    assert cache.get("k") is None         # expired


def test_cache_miss_returns_none() -> None:
    assert TTLCache().get("absent") is None
