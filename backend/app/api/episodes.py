"""Episodes router — list, detail, status polling (PRD 6)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Episode, GenerationJob, PlayEvent, User
from app.schemas.episode import (
    EpisodeDetail,
    EpisodeStatusResponse,
    EpisodeSummary,
    StageStatus,
)
from app.services.audio.storage import AUDIO_DIR, AUDIO_URL_PREFIX

router = APIRouter(tags=["episodes"])


def _delete_audio_file(audio_url: str | None) -> None:
    """Best-effort removal of an episode's MP3 from local storage.

    ``audio_url`` is a public path like ``/audio/episode_14.mp3``; map it back
    to the file on disk. Never raises — a missing file is fine (ephemeral
    storage may have already dropped it).
    """
    if not audio_url or not audio_url.startswith(f"{AUDIO_URL_PREFIX}/"):
        return
    filename = audio_url[len(AUDIO_URL_PREFIX) + 1 :]
    # Guard against path traversal from a malformed url.
    if "/" in filename or ".." in filename:
        return
    try:
        (Path(AUDIO_DIR) / filename).unlink(missing_ok=True)
    except OSError:
        pass


class ProgressIn(BaseModel):
    position_sec: int = Field(ge=0)


@router.get("/episodes", response_model=list[EpisodeSummary])
async def list_episodes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Episode]:
    rows = (
        await db.execute(
            select(Episode)
            .where(Episode.user_id == user.id)
            .order_by(Episode.episode_date.desc(), Episode.id.desc())
        )
    ).scalars().all()
    return list(rows)


@router.get("/episodes/{episode_id}", response_model=EpisodeDetail)
async def get_episode(
    episode_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Episode:
    episode = (
        await db.execute(
            select(Episode)
            .options(selectinload(Episode.stories))
            .where(Episode.id == episode_id, Episode.user_id == user.id)
        )
    ).scalar_one_or_none()
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    return episode


@router.get("/episodes/{episode_id}/status", response_model=EpisodeStatusResponse)
async def episode_status(
    episode_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EpisodeStatusResponse:
    episode = (
        await db.execute(
            select(Episode).where(
                Episode.id == episode_id, Episode.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")

    jobs = (
        await db.execute(
            select(GenerationJob)
            .where(GenerationJob.episode_id == episode_id)
            .order_by(GenerationJob.id)
        )
    ).scalars().all()

    return EpisodeStatusResponse(
        episode_id=episode.id,
        status=episode.status,
        error=episode.error,
        stages=[
            StageStatus(stage=j.stage, status=j.status, error=j.error) for j in jobs
        ],
    )


@router.post("/episodes/{episode_id}/progress", status_code=status.HTTP_204_NO_CONTENT)
async def record_progress(
    episode_id: int,
    payload: ProgressIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Append a play-position event (feeds listen-time / completion — PRD 10, 11.6)."""
    episode = (
        await db.execute(
            select(Episode).where(
                Episode.id == episode_id, Episode.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    db.add(PlayEvent(episode_id=episode_id, position_sec=payload.position_sec))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/episodes", status_code=status.HTTP_204_NO_CONTENT)
async def clear_episodes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete ALL of the user's episodes (and their audio). Clears history."""
    episodes = (
        await db.execute(select(Episode).where(Episode.user_id == user.id))
    ).scalars().all()
    for episode in episodes:
        _delete_audio_file(episode.audio_url)
        # Related stories/jobs/play_events cascade via the ORM relationships.
        await db.delete(episode)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/episodes/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode(
    episode_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a single episode (and its audio file)."""
    episode = (
        await db.execute(
            select(Episode).where(
                Episode.id == episode_id, Episode.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    _delete_audio_file(episode.audio_url)
    await db.delete(episode)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
