"""Pydantic schemas for the news domain (PRD 7).

``Article`` is the normalized shape every provider maps into. ``content_depth``
lets downstream AI stages know whether an article has full body text or only an
RSS snippet, so Stage 1 can summarize conservatively (PRD 8).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ContentDepth(StrEnum):
    FULL = "full"        # full-text extraction succeeded
    SNIPPET = "snippet"  # only title + RSS description available


class Article(BaseModel):
    """Normalized article from any provider."""

    title: str
    source: str
    url: str
    published_at: datetime
    content: str = ""
    # Popularity signal (e.g. HN points); providers set when available.
    popularity: float = 0.0
    content_depth: ContentDepth = ContentDepth.SNIPPET


class RankedArticle(BaseModel):
    """An article plus its computed ranking score and sub-scores (transparency)."""

    article: Article
    score: float
    subscores: dict[str, float] = Field(default_factory=dict)


class NewsItem(BaseModel):
    """API-facing shape for GET /api/news (a ranked story, no raw body text)."""

    title: str
    source: str
    url: str
    published_at: datetime
    summary: str
    score: float


class NewsResponse(BaseModel):
    items: list[NewsItem]
    cached: bool
