"""Seed the demo user and preferences (PRD 1.3, 5, 13).

Idempotent: safe to run repeatedly (docker-compose, tests, manual). The single
seeded user is the "demo listener". Analytics history seeding was removed with
the seeded concept, so the dashboard shows only real captured data.

Run: `python -m app.seed.seed`
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Length, Preference, Tone, User, Voice

DEMO_EMAIL = "demo@prosper.ai"
DEMO_NAME = "Demo Listener"
DEMO_INTERESTS = ["technology", "space", "science", "world news"]


async def seed_user(session) -> User:
    existing = (
        await session.execute(select(User).where(User.email == DEMO_EMAIL))
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    user = User(name=DEMO_NAME, email=DEMO_EMAIL)
    session.add(user)
    await session.flush()
    return user


async def seed_preference(session, user: User) -> None:
    existing = (
        await session.execute(
            select(Preference).where(Preference.user_id == user.id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return
    session.add(
        Preference(
            user_id=user.id,
            interests=DEMO_INTERESTS,
            voice=Voice.RACHEL,
            tone=Tone.PROFESSIONAL,
            podcast_length=Length.MEDIUM,
            schedule="07:00",
        )
    )


async def run_seed() -> None:
    async with SessionLocal() as session:
        user = await seed_user(session)
        await seed_preference(session, user)
        await session.commit()
    print("[seed] demo user and preferences ready.")


if __name__ == "__main__":
    asyncio.run(run_seed())
