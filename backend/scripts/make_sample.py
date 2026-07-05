"""Headless full-pipeline run that produces sample.mp3 (PRD 8, 13, 14).

Runs the exact same orchestrator the app uses (news -> 3-stage AI -> ElevenLabs
-> merge -> store), then copies the resulting episode MP3 to the repo root as
sample.mp3. Requires OPENAI_API_KEY and ELEVENLABS_API_KEY and a reachable
Postgres (docker-compose provides both).

Usage (inside the backend container):
    python -m scripts.make_sample
Optional: --interests "space,ai" --length medium --voice rachel
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
from datetime import date
from pathlib import Path

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import (
    Episode,
    EpisodeStatus,
    GenerationJob,
    Length,
    Preference,
    Story,
    User,
    Voice,
)
from app.services.ai.factory import build_llm_client
from app.services.audio.factory import build_audio_hook
from app.services.audio.storage import AUDIO_DIR
from app.services.generation.orchestrator import generate_episode
from app.services.news.service import NewsService

SAMPLE_OUT = Path("/app/sample_out")  # mounted so the file lands on the host repo


SAMPLE_EMAIL = "sample@prosper.ai"


async def _ensure_user(session, interests: list[str], length: Length, voice: Voice) -> User:
    """A dedicated sample user, so the demo user's preferences are untouched."""
    user = (
        await session.execute(select(User).where(User.email == SAMPLE_EMAIL))
    ).scalar_one_or_none()
    if user is None:
        user = User(name="Sample Listener", email=SAMPLE_EMAIL)
        session.add(user)
        await session.flush()
    pref = (
        await session.execute(select(Preference).where(Preference.user_id == user.id))
    ).scalar_one_or_none()
    if pref is None:
        pref = Preference(user_id=user.id, interests=interests)
        session.add(pref)
    pref.interests = interests
    pref.podcast_length = length
    pref.voice = voice
    await session.commit()
    return user


async def run(interests: list[str], length: Length, voice: Voice) -> None:
    settings = get_settings()
    if not settings.openai_api_key or not settings.elevenlabs_api_key:
        raise SystemExit("OPENAI_API_KEY and ELEVENLABS_API_KEY are required.")

    async with SessionLocal() as session:
        user = await _ensure_user(session, interests, length, voice)

        # Reuse (or create) today's sample episode for the sample user. A rerun
        # on the same day resets and regenerates the same row instead of piling
        # up episodes; the demo user's own episodes are never touched.
        sample_date = date.today()
        existing = (
            (
                await session.execute(
                    select(Episode)
                    .where(
                        Episode.user_id == user.id,
                        Episode.episode_date == sample_date,
                    )
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
        if existing is not None:
            await session.execute(delete(Story).where(Story.episode_id == existing.id))
            await session.execute(
                delete(GenerationJob).where(GenerationJob.episode_id == existing.id)
            )
            episode = existing
            episode.status = EpisodeStatus.PENDING
            episode.audio_url = None
        else:
            episode = Episode(
                user_id=user.id, episode_date=sample_date, status=EpisodeStatus.PENDING
            )
            session.add(episode)
        await session.commit()
        episode_id = episode.id

        print(f"[make_sample] generating episode {episode_id} ...")
        await generate_episode(
            session,
            episode_id,
            llm_client=build_llm_client(),
            news_service=NewsService(),
            audio_hook=build_audio_hook(session),
        )

        refreshed = (
            await session.execute(select(Episode).where(Episode.id == episode_id))
        ).scalar_one()
        if refreshed.status != EpisodeStatus.READY or not refreshed.audio_url:
            raise SystemExit(f"generation failed: {refreshed.error}")

        print(f"[make_sample] title:    {refreshed.title}")
        print(f"[make_sample] duration: {refreshed.duration_sec}s")

        # audio_url is /audio/<file>; source lives under AUDIO_DIR.
        filename = refreshed.audio_url.rsplit("/", 1)[-1]
        src = Path(AUDIO_DIR) / filename
        SAMPLE_OUT.mkdir(parents=True, exist_ok=True)
        dst = SAMPLE_OUT / "sample.mp3"
        shutil.copyfile(src, dst)
        print(f"[make_sample] wrote {dst}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interests", default="technology,space,science,world news")
    parser.add_argument("--length", default="medium", choices=[e.value for e in Length])
    parser.add_argument("--voice", default="rachel", choices=[e.value for e in Voice])
    args = parser.parse_args()

    interests = [i.strip() for i in args.interests.split(",") if i.strip()]
    asyncio.run(run(interests, Length(args.length), Voice(args.voice)))


if __name__ == "__main__":
    main()
