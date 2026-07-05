"""Generation router — POST /api/generate (PRD 4.2, 6).

Revision (user-requested): multiple episodes per day are allowed, so every call
creates a NEW episode and runs the pipeline. To keep a stuck button or direct
API spam from fanning out into parallel paid pipelines, a request is rejected
with 409 while the user already has an episode in flight (bounded by the
generation timeout so a stale row can never block forever).
Returns 202 + episode id; the pipeline runs in a BackgroundTask (injected, so
tests substitute a synchronous stub).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user, get_generation_runner
from app.core.ratelimit import rate_limit_generate
from app.db.session import get_db
from app.models import Episode, EpisodeStatus, User
from app.schemas.episode import GenerateResponse

router = APIRouter(tags=["generate"])


@router.post("/generate", response_model=GenerateResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate(
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    runner=Depends(get_generation_runner),
    _rl: None = Depends(rate_limit_generate),
) -> GenerateResponse:
    """Create a new episode for the current user and start generation."""
    cutoff = datetime.now(UTC) - timedelta(
        seconds=get_settings().generation_timeout_sec
    )
    in_flight = (
        await db.execute(
            select(Episode.id)
            .where(
                Episode.user_id == user.id,
                Episode.status.in_([EpisodeStatus.PENDING, EpisodeStatus.GENERATING]),
                Episode.created_at > cutoff,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if in_flight is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An episode is already being generated. Please wait for it to finish.",
        )

    episode = Episode(
        user_id=user.id, episode_date=date.today(), status=EpisodeStatus.PENDING
    )
    db.add(episode)
    await db.commit()
    await db.refresh(episode)

    background.add_task(runner, episode.id)
    return GenerateResponse(
        episode_id=episode.id, status=EpisodeStatus.PENDING, created=True
    )
