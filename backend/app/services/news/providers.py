"""News providers (PRD 7).

Each provider maps a source into the normalized ``Article`` shape. Providers run
concurrently and are isolated by the collector, so one failing provider never
sinks the batch. Network parsing is kept behind small seams so tests can feed
recorded fixtures instead of hitting the network (PRD 11.5).
"""

from __future__ import annotations

from datetime import UTC, datetime
from time import mktime
from typing import Protocol

import feedparser
import httpx

from app.core.retry import with_retry
from app.schemas.news import Article, ContentDepth

DEFAULT_TIMEOUT = 10.0


class NewsProvider(Protocol):
    name: str

    async def fetch(self) -> list[Article]: ...


def _parse_struct_time(value: object) -> datetime:
    """feedparser time struct → aware UTC datetime; fall back to now."""
    if value:
        try:
            return datetime.fromtimestamp(mktime(value), tz=UTC)  # type: ignore[arg-type]
        except (TypeError, ValueError, OverflowError):
            pass
    return datetime.now(UTC)


def parse_rss(source: str, feed_bytes: bytes) -> list[Article]:
    """Parse raw RSS/Atom bytes into Articles. Pure → unit-testable."""
    parsed = feedparser.parse(feed_bytes)
    articles: list[Article] = []
    for entry in parsed.entries:
        link = entry.get("link")
        title = entry.get("title")
        if not link or not title:
            continue
        published = _parse_struct_time(
            entry.get("published_parsed") or entry.get("updated_parsed")
        )
        summary = entry.get("summary", "") or ""
        articles.append(
            Article(
                title=title,
                source=source,
                url=link,
                published_at=published,
                content=summary,
                content_depth=ContentDepth.SNIPPET,
            )
        )
    return articles


class RSSProvider:
    """Generic RSS provider. One instance per feed."""

    def __init__(self, name: str, url: str, *, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.name = name
        self.url = url
        self._timeout = timeout

    async def fetch(self) -> list[Article]:
        async def _call() -> list[Article]:
            async with httpx.AsyncClient(
                timeout=self._timeout, follow_redirects=True
            ) as client:
                resp = await client.get(self.url)
                resp.raise_for_status()
                return parse_rss(self.name, resp.content)

        return await with_retry(_call, label=f"rss.{self.name}")


def parse_hackernews(items: list[dict]) -> list[Article]:
    """Map HN API story dicts into Articles. Pure → unit-testable."""
    articles: list[Article] = []
    for item in items:
        if not item or item.get("type") != "story":
            continue
        url = item.get("url") or f"https://news.ycombinator.com/item?id={item.get('id')}"
        title = item.get("title")
        if not title:
            continue
        published = datetime.fromtimestamp(item.get("time", 0), tz=UTC)
        articles.append(
            Article(
                title=title,
                source="Hacker News",
                url=url,
                published_at=published,
                content=title,
                popularity=float(item.get("score", 0)),
                content_depth=ContentDepth.SNIPPET,
            )
        )
    return articles


class HackerNewsProvider:
    """Hacker News top stories via the public Firebase API."""

    name = "Hacker News"
    _TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
    _ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"

    def __init__(self, *, limit: int = 20, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._limit = limit
        self._timeout = timeout

    async def fetch(self) -> list[Article]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            top = (await client.get(self._TOP)).json()[: self._limit]
            items: list[dict] = []
            for story_id in top:
                resp = await client.get(self._ITEM.format(id=story_id))
                if resp.status_code == 200 and resp.json():
                    items.append(resp.json())
        return parse_hackernews(items)


def default_providers() -> list[NewsProvider]:
    """The default provider set (PRD 7). Pluggable; resilient to any one failing.

    Feeds span general, tech, science, and sports so a range of interests has
    matching supply. BBC Sport + ESPN give sports-focused users real coverage.
    """
    return [
        RSSProvider("BBC", "https://feeds.bbci.co.uk/news/rss.xml"),
        RSSProvider("BBC Sport", "https://feeds.bbci.co.uk/sport/rss.xml"),
        RSSProvider("ESPN", "https://www.espn.com/espn/rss/news"),
        RSSProvider("TechCrunch", "https://techcrunch.com/feed/"),
        RSSProvider("NASA", "https://www.nasa.gov/feed/"),
        HackerNewsProvider(),
    ]
