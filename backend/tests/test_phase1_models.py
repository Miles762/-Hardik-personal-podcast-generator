"""Phase 1 tests: data layer — models, relationships, enums, seed.

Runs on in-memory SQLite (no Postgres, no external APIs). Proves the schema that
later phases depend on.
"""

from datetime import date

from sqlalchemy import select

from app.models import (
    LENGTH_STORY_COUNT,
    VOICE_IDS,
    Episode,
    EpisodeStatus,
    Length,
    Preference,
    Tone,
    User,
    Voice,
)


async def _make_user(session, email: str = "a@b.com") -> User:
    user = User(name="Test", email=email)
    session.add(user)
    await session.flush()
    return user


async def test_create_user_and_preference(db_session) -> None:
    user = await _make_user(db_session)
    db_session.add(
        Preference(
            user_id=user.id,
            interests=["tech", "space"],
            voice=Voice.ADAM,
            tone=Tone.WITTY,
            podcast_length=Length.LONG,
            schedule="08:30",
        )
    )
    await db_session.commit()

    pref = (
        await db_session.execute(
            select(Preference).where(Preference.user_id == user.id)
        )
    ).scalar_one()
    assert pref.interests == ["tech", "space"]
    assert pref.voice == Voice.ADAM
    assert pref.schedule == "08:30"


async def test_multiple_episodes_per_day_allowed(db_session) -> None:
    """Revision: multiple episodes per user per day are allowed (constraint removed)."""
    user = await _make_user(db_session)
    today = date.today()
    db_session.add(Episode(user_id=user.id, episode_date=today))
    db_session.add(Episode(user_id=user.id, episode_date=today))
    await db_session.commit()  # must not raise

    from sqlalchemy import func

    count = (
        await db_session.execute(
            select(func.count()).select_from(Episode).where(Episode.user_id == user.id)
        )
    ).scalar_one()
    assert count == 2


async def test_same_date_different_users_allowed(db_session) -> None:
    u1 = await _make_user(db_session, "u1@x.com")
    u2 = await _make_user(db_session, "u2@x.com")
    today = date.today()
    db_session.add_all(
        [
            Episode(user_id=u1.id, episode_date=today),
            Episode(user_id=u2.id, episode_date=today),
        ]
    )
    await db_session.commit()  # must not raise


async def test_episode_status_defaults_pending(db_session) -> None:
    user = await _make_user(db_session)
    ep = Episode(user_id=user.id, episode_date=date.today())
    db_session.add(ep)
    await db_session.commit()
    await db_session.refresh(ep)
    assert ep.status == EpisodeStatus.PENDING


async def test_enum_lookup_tables_consistent() -> None:
    """Every Voice/Length maps to a config value (guards the audio/rank phases)."""
    for voice in Voice:
        assert voice in VOICE_IDS and VOICE_IDS[voice]
    for length in Length:
        assert length in LENGTH_STORY_COUNT


async def test_seed_is_idempotent(db_session, monkeypatch) -> None:
    """Running the seed twice yields exactly one user and one preference."""
    import app.seed.seed as seed_mod

    # Point the seed at the in-memory test session instead of the real engine.
    class _Maker:
        def __call__(self):
            return _Ctx(db_session)

    class _Ctx:
        def __init__(self, s):
            self._s = s

        async def __aenter__(self):
            return self._s

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(seed_mod, "SessionLocal", _Maker())

    await seed_mod.run_seed()
    await seed_mod.run_seed()

    users = (await db_session.execute(select(User))).scalars().all()
    prefs = (await db_session.execute(select(Preference))).scalars().all()
    assert len(users) == 1
    assert len(prefs) == 1
