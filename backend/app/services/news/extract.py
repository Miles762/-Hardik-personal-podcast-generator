"""Full-text extraction for the top-N ranked articles (PRD 7).

RSS descriptions are too thin to fact-ground a script on, so for the top-N only
we fetch the article URL and extract body text with trafilatura. On any failure
(paywall, JS page, timeout) we fall back to the RSS snippet and tag the article
``content_depth=snippet`` so Stage 1 summarizes conservatively (PRD 8).

Fetches run concurrently with a strict per-request timeout so one slow outlet
cannot stall the pipeline. The HTTP fetch and the trafilatura call are separate
seams so tests can inject HTML without network or the heavy parser.
"""

from __future__ import annotations

import asyncio

import httpx
import trafilatura

from app.schemas.news import Article, ContentDepth

# ~3k tokens ≈ ~12k chars (rough 4 chars/token). Cap before Stage 1 (PRD 7).
MAX_CHARS = 12_000
FETCH_TIMEOUT = 8.0


def extract_text(html: str) -> str | None:
    """Readability-style body extraction. Returns None if nothing usable."""
    if not html:
        return None
    return trafilatura.extract(html, include_comments=False, include_tables=False)


async def _fetch_html(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text
    except (httpx.HTTPError, httpx.InvalidURL):
        return None


async def enrich_article(client: httpx.AsyncClient, article: Article) -> Article:
    """Return a copy of ``article`` with full body text if extraction succeeds."""
    html = await _fetch_html(client, article.url)
    # trafilatura is CPU-bound (50-300ms on large pages); run it in a thread so
    # concurrent enrichment doesn't stall the event loop (same as merge_audio).
    body = (
        await asyncio.get_running_loop().run_in_executor(None, extract_text, html)
        if html
        else None
    )
    if not body:
        # Keep the RSS snippet; mark as snippet so the AI stage is conservative.
        return article.model_copy(update={"content_depth": ContentDepth.SNIPPET})
    return article.model_copy(
        update={"content": body[:MAX_CHARS], "content_depth": ContentDepth.FULL}
    )


async def enrich_top_n(articles: list[Article], *, timeout: float = FETCH_TIMEOUT) -> list[Article]:
    """Concurrently enrich the given (already top-N) articles. Order preserved."""
    if not articles:
        return []
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True, headers={"User-Agent": "PodcastBot/1.0"}
    ) as client:
        return list(
            await asyncio.gather(*(enrich_article(client, a) for a in articles))
        )
