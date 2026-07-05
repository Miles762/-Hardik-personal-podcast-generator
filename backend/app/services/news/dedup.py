"""Deduplication of collected articles (PRD 7).

Two-pass: exact URL match (normalized), then near-duplicate title match via
token Jaccard similarity. Pure and deterministic → unit-tested.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

from app.schemas.news import Article

_WORD_RE = re.compile(r"[a-z0-9]+")
TITLE_SIMILARITY_THRESHOLD = 0.8


def normalize_url(url: str) -> str:
    """Strip scheme differences, query, fragment, trailing slash, and 'www.'."""
    parts = urlsplit(url.strip().lower())
    netloc = parts.netloc.removeprefix("www.")
    path = parts.path.rstrip("/")
    return urlunsplit(("", netloc, path, "", ""))


def _title_tokens(title: str) -> frozenset[str]:
    return frozenset(_WORD_RE.findall(title.lower()))


def title_similarity(a: str, b: str) -> float:
    """Jaccard similarity of title token sets → [0, 1]."""
    ta, tb = _title_tokens(a), _title_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def deduplicate(articles: list[Article]) -> list[Article]:
    """Return articles with URL duplicates and near-duplicate titles removed.

    Keeps the first occurrence (providers are collected in a stable order).
    """
    seen_urls: set[str] = set()
    kept: list[Article] = []
    for article in articles:
        key = normalize_url(article.url)
        if key in seen_urls:
            continue
        if any(
            title_similarity(article.title, k.title) >= TITLE_SIMILARITY_THRESHOLD
            for k in kept
        ):
            continue
        seen_urls.add(key)
        kept.append(article)
    return kept
