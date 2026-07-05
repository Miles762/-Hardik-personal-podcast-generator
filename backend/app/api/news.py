"""News router — GET /api/news (PRD 6, 7).

Thin: validates, delegates to NewsService, maps to the API schema. No business
logic here (PRD 4 guiding principle).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user, get_news_service
from app.models import Length, User
from app.schemas.news import NewsItem, NewsResponse
from app.services.news.service import NewsService

router = APIRouter(tags=["news"])


@router.get("/news", response_model=NewsResponse)
async def get_news(
    user: User = Depends(get_current_user),
    news: NewsService = Depends(get_news_service),
) -> NewsResponse:
    """Current ranked news for the user, tailored to their interests + length."""
    pref = user.preference
    interests = pref.interests if pref else []
    length = pref.podcast_length if pref else Length.MEDIUM

    ranked, cached = await news.get_ranked(interests, length)
    items = [
        NewsItem(
            title=r.article.title,
            source=r.article.source,
            url=r.article.url,
            published_at=r.article.published_at,
            summary=(r.article.content[:280] if r.article.content else ""),
            score=round(r.score, 4),
        )
        for r in ranked
    ]
    return NewsResponse(items=items, cached=cached)
