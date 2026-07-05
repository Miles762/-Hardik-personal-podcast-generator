"""Analytics aggregation (PRD 10, 11.6).

Every value on the dashboard is a REAL captured number: latency from
GenerationJob timing, reliability from job statuses, listening from PlayEvent
rows, and user aggregates from preferences. The seeded concept was removed at the
user's request, so there is no Analytics-table history and no trend series.

Cost tiles were removed: jobs log total tokens but not the input/output split,
and output tokens are priced ~8x input, so any single-rate figure materially
understates real spend. Raw tokens/chars stay on the job rows for later use.
"""

from __future__ import annotations

from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Episode,
    EpisodeStatus,
    GenerationJob,
    JobStatus,
    PlayEvent,
    Preference,
)
from app.schemas.dashboard import (
    DashboardResponse,
    NameValue,
    Tile,
)


async def _avg_latency_sec(session: AsyncSession) -> float:
    """Average per-stage wall-clock from GenerationJob start/finish (real)."""
    rows = (
        await session.execute(
            select(GenerationJob.started_at, GenerationJob.finished_at).where(
                GenerationJob.finished_at.is_not(None),
                GenerationJob.started_at.is_not(None),
            )
        )
    ).all()
    if not rows:
        return 0.0
    durations = [(f - s).total_seconds() for s, f in rows]
    return round(sum(durations) / len(durations), 2)


async def _failed_jobs(session: AsyncSession) -> int:
    return (
        await session.execute(
            select(func.count()).select_from(GenerationJob).where(
                GenerationJob.status == JobStatus.FAILED
            )
        )
    ).scalar_one()


async def _avg_listen_and_completion(session: AsyncSession) -> tuple[float, float]:
    """Real listening metrics from PlayEvent rows (PRD 11.6)."""
    # Max position reached per episode = furthest listened.
    subq = (
        select(
            PlayEvent.episode_id.label("eid"),
            func.max(PlayEvent.position_sec).label("furthest"),
        )
        .group_by(PlayEvent.episode_id)
        .subquery()
    )
    rows = (
        await session.execute(
            select(subq.c.furthest, Episode.duration_sec).join(
                Episode, Episode.id == subq.c.eid
            )
        )
    ).all()
    if not rows:
        return 0.0, 0.0
    avg_listen = sum(r.furthest for r in rows) / len(rows)
    completions = [
        (r.furthest / r.duration_sec)
        for r in rows
        if r.duration_sec and r.duration_sec > 0
    ]
    completion = (sum(completions) / len(completions) * 100) if completions else 0.0
    return round(avg_listen, 1), round(completion, 1)


async def build_dashboard(session: AsyncSession) -> DashboardResponse:
    """Build the dashboard from real captured data only (no seeded values)."""
    # --- Operational tiles ---
    latency = await _avg_latency_sec(session)
    failed = await _failed_jobs(session)

    operational = [
        Tile(label="Avg Stage Latency", value=latency, unit="s"),
        Tile(label="Failed Jobs", value=float(failed)),
    ]

    # --- Product tiles ---
    episodes_generated = (
        await session.execute(
            select(func.count()).select_from(Episode).where(
                Episode.status == EpisodeStatus.READY
            )
        )
    ).scalar_one()
    avg_listen, completion = await _avg_listen_and_completion(session)

    product = [
        Tile(label="Podcasts Generated", value=float(episodes_generated)),
        Tile(label="Avg Listening Time", value=avg_listen, unit="s"),
        Tile(label="Completion Rate", value=completion, unit="%"),
    ]

    # --- User tiles (from preferences) ---
    prefs = (await session.execute(select(Preference))).scalars().all()
    interest_counter: Counter[str] = Counter()
    voice_counter: Counter[str] = Counter()
    lengths_minutes: list[int] = []
    from app.models import LENGTH_MINUTES, Length

    for p in prefs:
        interest_counter.update(p.interests or [])
        voice_counter.update([str(p.voice)])
        lengths_minutes.append(LENGTH_MINUTES[Length(p.podcast_length)])
    avg_len = round(sum(lengths_minutes) / len(lengths_minutes), 1) if lengths_minutes else 0.0

    user = [
        Tile(label="Tracked Interests", value=float(len(interest_counter))),
        Tile(label="Voices In Use", value=float(len(voice_counter))),
        Tile(label="Avg Episode Length", value=avg_len, unit="min"),
    ]

    top_interests = [
        NameValue(name=name, value=float(count))
        for name, count in interest_counter.most_common(6)
    ]
    voice_distribution = [
        NameValue(name=name, value=float(count)) for name, count in voice_counter.items()
    ]

    return DashboardResponse(
        product=product,
        user=user,
        operational=operational,
        top_interests=top_interests,
        voice_distribution=voice_distribution,
    )
