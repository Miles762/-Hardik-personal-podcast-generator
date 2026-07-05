"""In-process scheduling via APScheduler (PRD 3.2, 4.3).

One AsyncIOScheduler for the process. On startup we register a daily cron job per
user derived from their `schedule` preference ("HH:MM" in UTC, or None = off).
The manual button may create multiple episodes per day, but the scheduled job
skips the day if any episode already exists (check-then-insert below), so a
double fire or a manual run earlier in the day never produces a duplicate daily
episode. It runs the same `run_generation` seam the manual button uses: one code
path, two triggers.

Known limits (accepted for the take-home, PRD 4.3): jobs die with the process and
don't coordinate across nodes. Production path: Celery beat / cloud cron hitting
the same seam. The scheduler is created lazily and injected so tests never start a
real event-loop scheduler.
"""

from __future__ import annotations

import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Episode, EpisodeStatus, Preference

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


def _job_id(user_id: int) -> str:
    return f"generate-user-{user_id}"


async def _scheduled_generate(user_id: int) -> None:
    """Create today's episode for the user (idempotent) and run generation."""
    from app.services.generation.runner import run_generation

    async with SessionLocal() as session:
        today = date.today()
        existing = (
            await session.execute(
                select(Episode).where(
                    Episode.user_id == user_id, Episode.episode_date == today
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            logger.info("scheduled run: episode already exists for user %s", user_id)
            return
        episode = Episode(
            user_id=user_id, episode_date=today, status=EpisodeStatus.PENDING
        )
        session.add(episode)
        await session.commit()
        episode_id = episode.id
    await run_generation(episode_id)


def register_user_job(user_id: int, schedule: str | None) -> None:
    """(Re)register or remove a user's daily job. schedule is 'HH:MM' or None."""
    sched = get_scheduler()
    job_id = _job_id(user_id)
    if sched.get_job(job_id):
        sched.remove_job(job_id)
    if not schedule:
        return
    hour, minute = (int(x) for x in schedule.split(":"))
    sched.add_job(
        _scheduled_generate,
        trigger=CronTrigger(hour=hour, minute=minute),
        id=job_id,
        args=[user_id],
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("registered daily job for user %s at %s UTC", user_id, schedule)


async def start_scheduler() -> None:
    """Start the scheduler and register a job for every user with a schedule."""
    sched = get_scheduler()
    async with SessionLocal() as session:
        prefs = (
            await session.execute(
                select(Preference).where(Preference.schedule.is_not(None))
            )
        ).scalars().all()
    for pref in prefs:
        register_user_job(pref.user_id, pref.schedule)
    if not sched.running:
        sched.start()
    logger.info("scheduler started with %d user job(s)", len(prefs))


def shutdown_scheduler() -> None:
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
