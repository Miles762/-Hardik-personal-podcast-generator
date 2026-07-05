"""Phase 2 tests: provider parsing + collector isolation + extraction (PRD 7, 11.5).

No network: RSS/HN parsing runs on fixture bytes; the collector is exercised with
a fake failing provider to prove one failure != total failure.
"""


from datetime import UTC

from app.schemas.news import Article, ContentDepth
from app.services.news.extract import enrich_article, extract_text
from app.services.news.providers import parse_hackernews, parse_rss
from app.services.news.service import collect

RSS_FIXTURE = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>First Story</title>
    <link>https://example.com/first</link>
    <description>A short summary.</description>
    <pubDate>Wed, 01 Jan 2025 12:00:00 GMT</pubDate>
  </item>
  <item>
    <title>Second Story</title>
    <link>https://example.com/second</link>
    <description>Another summary.</description>
  </item>
</channel></rss>"""


def test_parse_rss_maps_fields() -> None:
    articles = parse_rss("BBC", RSS_FIXTURE)
    assert len(articles) == 2
    assert articles[0].title == "First Story"
    assert articles[0].source == "BBC"
    assert articles[0].url == "https://example.com/first"
    assert articles[0].content == "A short summary."


def test_parse_rss_skips_items_without_link_or_title() -> None:
    bad = b"""<rss version="2.0"><channel>
      <item><description>no title or link</description></item>
    </channel></rss>"""
    assert parse_rss("X", bad) == []


def test_parse_hackernews_maps_score_as_popularity() -> None:
    items = [
        {"type": "story", "id": 1, "title": "HN Post", "url": "https://h.com/x",
         "time": 1735732800, "score": 250},
        {"type": "job", "id": 2, "title": "skip me"},  # non-story ignored
    ]
    articles = parse_hackernews(items)
    assert len(articles) == 1
    assert articles[0].source == "Hacker News"
    assert articles[0].popularity == 250.0


class _FakeProvider:
    def __init__(self, name, articles=None, fail=False):
        self.name = name
        self._articles = articles or []
        self._fail = fail

    async def fetch(self):
        if self._fail:
            raise RuntimeError("provider down")
        return self._articles


def _article(title: str) -> Article:
    from datetime import datetime

    return Article(
        title=title, source="X", url=f"https://x.com/{title}",
        published_at=datetime.now(UTC),
    )


async def test_collector_isolates_provider_failure() -> None:
    """PRD 7/11.1: one failing provider must not sink the batch."""
    providers = [
        _FakeProvider("good", [_article("a"), _article("b")]),
        _FakeProvider("bad", fail=True),
        _FakeProvider("good2", [_article("c")]),
    ]
    articles = await collect(providers)
    assert {a.title for a in articles} == {"a", "b", "c"}


def test_extract_text_empty_returns_none() -> None:
    assert extract_text("") is None


async def test_enrich_article_falls_back_to_snippet(monkeypatch) -> None:
    """On fetch failure, keep snippet + tag content_depth=snippet (PRD 7/8)."""
    from app.services.news import extract as extract_mod

    async def _fail_fetch(client, url):
        return None

    monkeypatch.setattr(extract_mod, "_fetch_html", _fail_fetch)
    art = _article("news").model_copy(update={"content": "rss snippet"})
    result = await enrich_article(client=None, article=art)  # client unused on failure
    assert result.content == "rss snippet"
    assert result.content_depth == ContentDepth.SNIPPET


async def test_enrich_article_uses_full_text(monkeypatch) -> None:
    from app.services.news import extract as extract_mod

    async def _ok_fetch(client, url):
        return "<html><body>irrelevant</body></html>"

    monkeypatch.setattr(extract_mod, "_fetch_html", _ok_fetch)
    monkeypatch.setattr(extract_mod, "extract_text", lambda html: "Full body text.")
    art = _article("news").model_copy(update={"content": "snippet"})
    result = await enrich_article(client=None, article=art)
    assert result.content == "Full body text."
    assert result.content_depth == ContentDepth.FULL
