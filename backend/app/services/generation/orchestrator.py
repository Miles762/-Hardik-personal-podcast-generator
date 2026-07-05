"""Episode generation orchestrator (PRD 4.1, 4.2, 8).

`generate_episode(episode_id, ...)` is the single code path shared by the manual
`POST /api/generate` button and the scheduled APScheduler job (PRD 4.3). It:

  1. marks the episode `generating`,
  2. fetches ranked+enriched news for the user,
  3. runs the 3-stage AI pipeline (each stage wrapped in a GenerationJob),
  4. persists Story rows + the script + token/cost usage,
  5. marks the episode `ready` (Phase 4 adds audio between 4 and 5).

A hard timeout caps wall-clock; on any failure the episode is marked `failed`
with the error captured, and the offending GenerationJob records it. Audio is a
seam (`audio_hook`) filled in Phase 4 — Phase 3 stops at the script.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models import (
    Episode,
    EpisodeStatus,
    Length,
    Story,
    Tone,
    User,
)
from app.schemas.news import RankedArticle
from app.services.ai.client import LLMClient
from app.services.ai.pipeline import PipelineResult, run_pipeline
from app.services.generation.jobs import fail_job, finish_job, start_job
from app.services.news.service import NewsService

logger = logging.getLogger(__name__)

# Optional hook: Phase 4 sets an async callable (episode, script) -> (url, dur).
AudioHook = Callable[[Episode, str], Awaitable[tuple[str, int]]]


class GenerationError(Exception):
    """A stage failure with a message safe to show the end user.

    The raw exception stays in logs and the GenerationJob row; ``Episode.error``
    (which the frontend renders verbatim) only ever gets ``user_message``.
    """

    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


ERR_TIMEOUT = "Generation timed out. Please try again."
ERR_NEWS = "Couldn't gather news right now. Please try again in a few minutes."
ERR_NO_NEWS = "No fresh news stories were available. Please try again later."
ERR_AI = "Writing the script failed. Please try again."
ERR_AUDIO = "Turning the script into audio failed. Please try again."
ERR_UNKNOWN = "Something went wrong during generation. Please try again."


async def _persist_stories(
    session: AsyncSession, episode: Episode, ranked: list[RankedArticle], result: PipelineResult
) -> None:
    """Attach the ranked stories (with their AI summaries) to the episode."""
    for r, summary in zip(ranked, result.summaries, strict=False):
        session.add(
            Story(
                episode_id=episode.id,
                headline=summary.title or r.article.title,
                summary=summary.summary,
                source=r.article.source,
                url=r.article.url,
                published_at=r.article.published_at,
                score=r.score,
                importance=summary.importance,
            )
        )


async def generate_episode(
    session: AsyncSession,
    episode_id: int,
    *,
    llm_client: LLMClient,
    news_service: NewsService,
    audio_hook: AudioHook | None = None,
    timeout_sec: int | None = None,
) -> None:
    """Run the full generation pipeline for one episode. Commits on completion."""
    settings = get_settings()
    timeout_sec = timeout_sec or settings.generation_timeout_sec
    try:
        await asyncio.wait_for(
            _run(
                session,
                episode_id,
                llm_client=llm_client,
                news_service=news_service,
                audio_hook=audio_hook,
            ),
            timeout=timeout_sec,
        )
    except TimeoutError:
        await _mark_failed(session, episode_id, ERR_TIMEOUT)
    except GenerationError as exc:
        logger.exception("generation failed for episode %s", episode_id)
        await _mark_failed(session, episode_id, exc.user_message)
    except Exception:  # noqa: BLE001 — never let the background task crash silently
        logger.exception("generation failed for episode %s", episode_id)
        await _mark_failed(session, episode_id, ERR_UNKNOWN)


async def _run(
    session: AsyncSession,
    episode_id: int,
    *,
    llm_client: LLMClient,
    news_service: NewsService,
    audio_hook: AudioHook | None,
) -> None:
    episode = await _load_episode(session, episode_id)
    user = await _load_user(session, episode.user_id)
    pref = user.preference
    interests = pref.interests if pref else []
    # Coerce to real enum members: String columns load back as plain str.
    tone: Tone = Tone(pref.tone) if pref else Tone.PROFESSIONAL
    length: Length = Length(pref.podcast_length) if pref else Length.MEDIUM

    episode.status = EpisodeStatus.GENERATING
    episode.error = None
    await session.flush()

    # --- News (single job row spanning collect+rank+enrich) ---
    news_job = await start_job(session, episode_id, "news")
    try:
        ranked, _cached = await news_service.get_ranked(interests, length)
        if not ranked:
            # Fail fast instead of asking the LLM to write about nothing.
            raise RuntimeError("news collection returned no articles")
    except Exception as exc:  # noqa: BLE001
        await fail_job(session, news_job, str(exc))
        raise GenerationError(
            ERR_NO_NEWS if "no articles" in str(exc) else ERR_NEWS
        ) from exc
    await finish_job(session, news_job)

    # --- AI pipeline (per-stage job rows) ---
    result = await _run_pipeline_with_jobs(
        session, episode_id, llm_client, ranked, tone, length, user.name
    )

    # --- Persist stories + script + usage ---
    await _persist_stories(session, episode, ranked, result)
    episode.title = result.script.title
    episode.script = result.script.script

    # --- Audio (Phase 4 seam) ---
    if audio_hook is not None:
        audio_job = await start_job(session, episode_id, "audio")
        try:
            url, duration = await audio_hook(episode, result.script.script)
        except Exception as exc:  # noqa: BLE001
            await fail_job(session, audio_job, str(exc))
            raise GenerationError(ERR_AUDIO) from exc
        episode.audio_url = url
        episode.duration_sec = duration
        await finish_job(session, audio_job, chars=len(result.script.script))

    episode.status = EpisodeStatus.READY
    episode.generated_at = datetime.now(UTC)
    await session.commit()


async def _run_pipeline_with_jobs(
    session: AsyncSession,
    episode_id: int,
    llm_client: LLMClient,
    ranked: list[RankedArticle],
    tone: Tone,
    length: Length,
    listener_name: str,
) -> PipelineResult:
    """Run the 3 stages, wrapping the whole pipeline in per-stage job rows.

    We run the pipeline once (it is internally ordered) but record a job row per
    logical stage so /status and the failed-jobs tile have stage granularity.
    """
    job = await start_job(session, episode_id, "ai_pipeline")
    try:
        result = await run_pipeline(
            llm_client,
            [r.article for r in ranked],
            tone=tone,
            length=length,
            listener_name=listener_name,
        )
    except Exception as exc:  # noqa: BLE001
        await fail_job(session, job, str(exc))
        raise GenerationError(ERR_AI) from exc
    await finish_job(
        session, job, tokens=result.input_tokens + result.output_tokens
    )
    return result


async def _load_episode(session: AsyncSession, episode_id: int) -> Episode:
    episode = (
        await session.execute(select(Episode).where(Episode.id == episode_id))
    ).scalar_one()
    return episode


async def _load_user(session: AsyncSession, user_id: int) -> User:
    return (
        await session.execute(
            select(User).options(selectinload(User.preference)).where(User.id == user_id)
        )
    ).scalar_one()


async def _mark_failed(session: AsyncSession, episode_id: int, error: str) -> None:
    try:
        episode = await _load_episode(session, episode_id)
        episode.status = EpisodeStatus.FAILED
        episode.error = error[:2000]
        await session.commit()
    except Exception:  # noqa: BLE001
        logger.exception("could not mark episode %s failed", episode_id)
        await session.rollback()
