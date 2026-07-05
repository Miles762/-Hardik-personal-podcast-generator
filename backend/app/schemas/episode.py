"""API schemas for episodes + generation (PRD 6)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.models import EpisodeStatus


class StoryOut(BaseModel):
    headline: str
    summary: str | None
    source: str
    url: str
    published_at: datetime | None
    score: float | None
    importance: int | None

    model_config = {"from_attributes": True}


class EpisodeSummary(BaseModel):
    """List-view shape (history)."""

    id: int
    episode_date: date
    title: str | None
    status: EpisodeStatus
    duration_sec: int | None
    audio_url: str | None
    created_at: datetime
    generated_at: datetime | None

    model_config = {"from_attributes": True}


class EpisodeDetail(EpisodeSummary):
    """Detail-view shape (player): adds script + stories."""

    script: str | None
    error: str | None
    stories: list[StoryOut] = []


class GenerateResponse(BaseModel):
    """202 body from POST /api/generate."""

    episode_id: int
    status: EpisodeStatus
    created: bool  # False when returning an existing (idempotent) episode


class StageStatus(BaseModel):
    stage: str
    status: str
    error: str | None


class EpisodeStatusResponse(BaseModel):
    """GET /api/episodes/{id}/status — polling shape."""

    episode_id: int
    status: EpisodeStatus
    error: str | None
    stages: list[StageStatus]
