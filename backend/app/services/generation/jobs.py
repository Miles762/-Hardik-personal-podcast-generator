"""GenerationJob helpers — per-stage lifecycle records (PRD 4.2, 11.6).

Every pipeline stage opens a job row (running), then closes it (done/failed) with
timing and token counts. These rows power the /status endpoint, the progress
indicator, and the analytics operational tiles.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GenerationJob, JobStatus


async def start_job(session: AsyncSession, episode_id: int, stage: str) -> GenerationJob:
    job = GenerationJob(
        episode_id=episode_id,
        stage=stage,
        status=JobStatus.RUNNING,
        started_at=datetime.now(UTC),
    )
    session.add(job)
    await session.flush()
    return job


async def finish_job(
    session: AsyncSession,
    job: GenerationJob,
    *,
    tokens: int | None = None,
    chars: int | None = None,
) -> None:
    job.status = JobStatus.DONE
    job.finished_at = datetime.now(UTC)
    job.tokens = tokens
    job.chars = chars
    await session.flush()


async def fail_job(session: AsyncSession, job: GenerationJob, error: str) -> None:
    job.status = JobStatus.FAILED
    job.error = error[:2000]
    job.finished_at = datetime.now(UTC)
    await session.flush()
