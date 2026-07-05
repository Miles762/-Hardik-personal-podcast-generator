"""Shared FastAPI dependencies (PRD 11.4 — dependency injection).

Single-user MVP (PRD 1.3): "current user" resolves to the seeded demo user. The
seam is a dependency, so real auth can replace it later without touching routers.
The NewsService is a process-lifetime singleton so its 1-hour cache is shared.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models import User
from app.services.news.service import NewsService

_news_service = NewsService()


def get_news_service() -> NewsService:
    return _news_service


def get_generation_runner():
    """Return the callable BackgroundTasks invokes to run generation.

    A dependency so tests can override it with a synchronous stub (no OpenAI,
    no BackgroundTasks event-loop coupling). Imported lazily to avoid a circular
    import (runner imports this module).
    """
    from app.services.generation.runner import run_generation

    return run_generation


async def get_current_user(db: AsyncSession = Depends(get_db)) -> User:
    """Resolve the demo user with preferences eagerly loaded."""
    user = (
        await db.execute(
            select(User).options(selectinload(User.preference)).limit(1)
        )
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="No user found. Run the seed script.")
    return user
