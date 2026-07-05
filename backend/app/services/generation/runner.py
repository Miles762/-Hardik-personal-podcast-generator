"""Background generation runner + startup orphan sweep (PRD 4.2).

`run_generation(episode_id)` is the thin seam FastAPI BackgroundTasks (and the
scheduler) invoke. It owns its own DB session and builds the real clients, then
delegates to the orchestrator. A queue/worker can replace this seam in prod
without touching the orchestrator.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from app.core.config import get_settings
from app.core.deps import get_news_service
from app.db.session import SessionLocal
from app.models import Episode, EpisodeStatus
from app.services.ai.factory import build_llm_client
from app.services.generation.orchestrator import generate_episode

logger = logging.getLogger(__name__)


async def run_generation(episode_id: int) -> None:
    """Entry point for background execution: full pipeline incl. audio (PRD 9)."""
    from app.services.audio.factory import build_audio_hook

    async with SessionLocal() as session:
        await generate_episode(
            session,
            episode_id,
            llm_client=build_llm_client(),
            news_service=get_news_service(),
            audio_hook=build_audio_hook(session),
        )


async def sweep_orphaned_episodes() -> int:
    """Mark episodes stuck in pending/generating past the timeout as failed.

    Called on app startup so a crash/restart mid-pipeline can never leave an
    episode permanently stuck (PRD 4.2). Returns the number swept.
    """
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.generation_timeout_sec)
    async with SessionLocal() as session:
        stale_ids = (
            await session.execute(
                select(Episode.id).where(
                    Episode.status.in_(
                        [EpisodeStatus.PENDING, EpisodeStatus.GENERATING]
                    ),
                    Episode.created_at < cutoff,
                )
            )
        ).scalars().all()
        if not stale_ids:
            return 0
        await session.execute(
            update(Episode)
            .where(Episode.id.in_(stale_ids))
            .values(status=EpisodeStatus.FAILED, error="orphaned by restart")
        )
        await session.commit()
        logger.warning("swept %d orphaned episodes", len(stale_ids))
        return len(stale_ids)
