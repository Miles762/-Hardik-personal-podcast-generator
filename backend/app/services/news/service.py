"""News service orchestrator (PRD 7).

Pipeline: collect (concurrent, isolated) → cache → dedup → rank → top-N →
full-text extraction. The collect+cache+dedup stage is cached for 1 hour and is
interest-independent; ranking and extraction run per request against the user's
interests and length.
"""

from __future__ import annotations

import asyncio
import logging

from app.models import LENGTH_STORY_COUNT, Length
from app.schemas.news import Article, RankedArticle
from app.services.news.cache import TTLCache
from app.services.news.dedup import deduplicate
from app.services.news.extract import enrich_top_n
from app.services.news.providers import NewsProvider, default_providers
from app.services.news.ranking import RankWeights, interest_score, rank_articles

logger = logging.getLogger(__name__)

_CACHE_KEY = "merged_news"


async def collect(providers: list[NewsProvider]) -> list[Article]:
    """Fetch all providers concurrently; isolate failures (PRD 7, 11.1)."""
    results = await asyncio.gather(
        *(p.fetch() for p in providers), return_exceptions=True
    )
    articles: list[Article] = []
    for provider, result in zip(providers, results, strict=True):
        if isinstance(result, BaseException):
            logger.warning("news provider %s failed: %s", provider.name, result)
            continue
        articles.extend(result)
    return articles


class NewsService:
    """Stateful across requests only via its 1-hour cache."""

    def __init__(
        self,
        providers: list[NewsProvider] | None = None,
        *,
        cache: TTLCache[list[Article]] | None = None,
    ) -> None:
        self._providers = providers if providers is not None else default_providers()
        self._cache: TTLCache[list[Article]] = cache or TTLCache()

    async def _collect_merged(self) -> tuple[list[Article], bool]:
        """Return (deduped articles, cached?). Caches the merged, deduped set."""
        cached = self._cache.get(_CACHE_KEY)
        if cached is not None:
            return cached, True
        raw = await collect(self._providers)
        merged = deduplicate(raw)
        self._cache.set(_CACHE_KEY, merged)
        return merged, False

    async def get_ranked(
        self,
        interests: list[str],
        length: Length = Length.MEDIUM,
        *,
        weights: RankWeights | None = None,
        enrich: bool = True,
    ) -> tuple[list[RankedArticle], bool]:
        """Full pipeline for a user. Returns (top-N ranked+enriched, cached?)."""
        merged, was_cached = await self._collect_merged()
        ranked = rank_articles(merged, interests, weights=weights)
        top_n = LENGTH_STORY_COUNT[length]
        top = self._select_top(ranked, interests, top_n)

        if enrich and top:
            enriched = await enrich_top_n([r.article for r in top])
            top = [
                RankedArticle(article=a, score=r.score, subscores=r.subscores)
                for a, r in zip(enriched, top, strict=True)
            ]
        return top, was_cached

    @staticmethod
    def _select_top(
        ranked: list[RankedArticle], interests: list[str], top_n: int
    ) -> list[RankedArticle]:
        """Pick the top N with balanced coverage across the user's interests.

        On-topic stories (interest score > 0) are assigned to the single interest
        each best matches, then selected round-robin: the best story for interest
        1, then interest 2, and so on, before any interest gets a second slot. So
        a multi-interest user hears from each of their picks instead of one hot
        topic sweeping every slot. Off-topic stories are dropped; if nothing
        matches at all, fall back to plain top-N so generation never starves.
        """
        if not interests:
            return ranked[:top_n]

        on_topic = [r for r in ranked if r.subscores.get("interest", 0.0) > 0.0]
        if not on_topic:
            return ranked[:top_n]

        # Bucket each on-topic article under the interest it matches best.
        buckets: dict[str, list[RankedArticle]] = {i: [] for i in interests}
        for r in on_topic:
            best_interest = max(
                interests, key=lambda i: interest_score(r.article, [i])
            )
            buckets[best_interest].append(r)
        # Each bucket stays in descending score order (on_topic already sorted).

        # Round-robin: take one story per interest per pass, best first.
        selected: list[RankedArticle] = []
        cursors = {i: 0 for i in interests}
        while len(selected) < top_n:
            progressed = False
            for i in interests:
                if len(selected) >= top_n:
                    break
                bucket = buckets[i]
                if cursors[i] < len(bucket):
                    selected.append(bucket[cursors[i]])
                    cursors[i] += 1
                    progressed = True
            if not progressed:  # all buckets exhausted
                break
        return selected
