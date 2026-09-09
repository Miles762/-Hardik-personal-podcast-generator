"""Article ranking (PRD 7).

score = w1*interest + w2*freshness + w3*popularity + w4*source_trust
with each sub-score normalized to [0, 1] before weighting.
Default weights (0.5, 0.2, 0.2, 0.1) — tunable, surfaced as a talking point.

All functions here are pure and deterministic → unit-tested without credits.

Interest similarity is keyword/TF-IDF against user interests (MVP decision,
PRD 7). The scorer sits behind a single ``score_article`` entry point so an
embedding-based similarity can be swapped in later (Liskov-safe).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime

from app.schemas.news import Article, RankedArticle

_WORD_RE = re.compile(r"[a-z0-9]+")

# Interest -> related terms. Real articles rarely contain the bare category word
# ("sports", "technology"): a football story says "goal"/"league", not "sports".
# Expanding each interest into its vocabulary lets keyword matching actually fire
# for topical stories instead of falling back to generic top-N (see service.py).
INTEREST_SYNONYMS: dict[str, tuple[str, ...]] = {
    "sports": (
        "sport", "football", "soccer", "nfl", "nba", "mlb", "nhl", "baseball",
        "basketball", "tennis", "golf", "cricket", "rugby", "hockey", "league",
        "playoff", "playoffs", "championship", "match", "goal", "coach",
        "athlete", "olympics", "fifa", "uefa", "premier", "quarterback",
        "striker", "touchdown", "tournament", "season", "team",
    ),
    "technology": (
        "tech", "software", "hardware", "ai", "startup", "app", "computing",
        "chip", "semiconductor", "gadget", "device", "iphone", "android",
        "cloud", "developer", "programming", "cybersecurity", "robot",
    ),
    "science": (
        "research", "study", "scientists", "physics", "biology", "chemistry",
        "genetics", "climate", "quantum", "experiment", "discovery",
    ),
    "space": (
        "nasa", "rocket", "orbit", "satellite", "spacecraft", "astronaut",
        "mars", "moon", "launch", "spacex", "galaxy", "telescope", "asteroid",
    ),
    "world news": (
        "world", "government", "election", "president", "minister", "war",
        "diplomacy", "economy", "international", "country", "policy",
    ),
    "business": (
        "market", "stocks", "economy", "revenue", "earnings", "investors",
        "acquisition", "ipo", "company", "trade", "finance",
    ),
    "politics": (
        "election", "senate", "congress", "president", "policy", "vote",
        "government", "campaign", "minister", "parliament",
    ),
    "health": (
        "medical", "disease", "vaccine", "hospital", "doctors", "wellness",
        "mental", "nutrition", "fitness", "medicine",
    ),
    "entertainment": (
        "movie", "film", "music", "celebrity", "hollywood", "streaming",
        "album", "concert", "tv", "show", "actor",
    ),
}


def _expand_interest_terms(interests: list[str]) -> set[str]:
    """Interest labels -> the set of match terms (label tokens + synonyms)."""
    terms: set[str] = set()
    for interest in interests:
        terms.update(_tokenize(interest))
        terms.update(INTEREST_SYNONYMS.get(interest.strip().lower(), ()))
    return terms

# Static per-source trust weights in [0, 1] (PRD 7). Unknown sources -> default.
SOURCE_TRUST: dict[str, float] = {
    "BBC": 0.95,
    "BBC Sport": 0.9,
    "ESPN": 0.85,
    "Reuters": 0.95,
    "TechCrunch": 0.8,
    "NASA": 0.9,
    "Hacker News": 0.6,
}
DEFAULT_SOURCE_TRUST = 0.5

FRESHNESS_HALFLIFE_HOURS = 12.0


@dataclass(frozen=True)
class RankWeights:
    interest: float = 0.5
    freshness: float = 0.2
    popularity: float = 0.2
    source_trust: float = 0.1


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def interest_score(article: Article, interests: list[str]) -> float:
    """TF-IDF-lite keyword overlap of article text vs. user interests → [0, 1].

    We weight article tokens by term frequency and count how much of that mass
    lands on interest terms (including multi-word interests split into tokens).
    Deterministic and zero-latency (PRD 7).
    """
    if not interests:
        return 0.0
    tokens = _tokenize(f"{article.title} {article.content}")
    if not tokens:
        return 0.0
    tf = Counter(tokens)
    total = sum(tf.values())

    interest_terms = _expand_interest_terms(interests)
    if not interest_terms:
        return 0.0

    matched = sum(count for term, count in tf.items() if term in interest_terms)
    # Diminishing returns: sqrt keeps a single keyword-stuffed article from
    # dominating while still rewarding genuine topical overlap.
    return min(1.0, math.sqrt(matched / total))


def freshness_score(published_at: datetime, *, now: datetime | None = None) -> float:
    """Exponential decay by age, half-life ≈ 12h → [0, 1] (PRD 7)."""
    now = now or datetime.now(UTC)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    age_hours = max(0.0, (now - published_at).total_seconds() / 3600.0)
    return 0.5 ** (age_hours / FRESHNESS_HALFLIFE_HOURS)


def popularity_score(popularity: float, *, cap: float = 1000.0) -> float:
    """Log-scaled popularity normalized to [0, 1] (PRD 7)."""
    if popularity <= 0:
        return 0.0
    return min(1.0, math.log1p(popularity) / math.log1p(cap))


def source_trust_score(source: str) -> float:
    """Static per-source trust in [0, 1] (PRD 7)."""
    return SOURCE_TRUST.get(source, DEFAULT_SOURCE_TRUST)


def score_article(
    article: Article,
    interests: list[str],
    *,
    weights: RankWeights | None = None,
    now: datetime | None = None,
) -> RankedArticle:
    """Compute the weighted score + sub-score breakdown for one article."""
    w = weights or RankWeights()
    subs = {
        "interest": interest_score(article, interests),
        "freshness": freshness_score(article.published_at, now=now),
        "popularity": popularity_score(article.popularity),
        "source_trust": source_trust_score(article.source),
    }
    score = (
        w.interest * subs["interest"]
        + w.freshness * subs["freshness"]
        + w.popularity * subs["popularity"]
        + w.source_trust * subs["source_trust"]
    )
    return RankedArticle(article=article, score=score, subscores=subs)


def rank_articles(
    articles: list[Article],
    interests: list[str],
    *,
    weights: RankWeights | None = None,
    now: datetime | None = None,
) -> list[RankedArticle]:
    """Score and sort articles descending by score."""
    ranked = [
        score_article(a, interests, weights=weights, now=now) for a in articles
    ]
    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked
