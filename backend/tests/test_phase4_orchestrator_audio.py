"""Phase 4: orchestrator with the audio hook -> full episode (PRD 9). Offline."""

from datetime import date

from sqlalchemy import select

from app.models import Episode, EpisodeStatus, GenerationJob, Length, Preference, User
from app.services.generation.orchestrator import generate_episode
from tests.fakes import FakeLLMClient, make_fake_news_service


async def _seed(session) -> Episode:
    u = User(name="Sam", email="sam@x.com")
    session.add(u)
    await session.flush()
    session.add(Preference(user_id=u.id, interests=["tech"], podcast_length=Length.SHORT))
    ep = Episode(user_id=u.id, episode_date=date.today(), status=EpisodeStatus.PENDING)
    session.add(ep)
    await session.commit()
    await session.refresh(ep)
    return ep


async def test_full_episode_has_audio(db_session) -> None:
    ep = await _seed(db_session)

    async def _audio_hook(episode, script):
        assert script                      # hook receives the finished script
        return "/audio/episode_test.mp3", 123

    await generate_episode(
        db_session, ep.id,
        llm_client=FakeLLMClient(),
        news_service=make_fake_news_service(2),
        audio_hook=_audio_hook,
    )

    refreshed = (await db_session.execute(select(Episode).where(Episode.id == ep.id))).scalar_one()
    assert refreshed.status == EpisodeStatus.READY
    assert refreshed.audio_url == "/audio/episode_test.mp3"
    assert refreshed.duration_sec == 123

    jobs = (await db_session.execute(select(GenerationJob).where(GenerationJob.episode_id == ep.id))).scalars().all()
    assert any(j.stage == "audio" for j in jobs)


async def test_audio_hook_failure_marks_episode_failed(db_session) -> None:
    ep = await _seed(db_session)

    async def _bad_hook(episode, script):
        raise RuntimeError("elevenlabs boom")

    await generate_episode(
        db_session, ep.id,
        llm_client=FakeLLMClient(),
        news_service=make_fake_news_service(1),
        audio_hook=_bad_hook,
    )

    refreshed = (await db_session.execute(select(Episode).where(Episode.id == ep.id))).scalar_one()
    assert refreshed.status == EpisodeStatus.FAILED
    # The user-facing error is friendly; the raw error lives on the job row.
    from app.services.generation.orchestrator import ERR_AUDIO
    assert refreshed.error == ERR_AUDIO
    jobs = (await db_session.execute(select(GenerationJob).where(GenerationJob.episode_id == ep.id))).scalars().all()
    from app.models import JobStatus
    audio_job = next(j for j in jobs if j.stage == "audio")
    assert audio_job.status == JobStatus.FAILED
    assert "boom" in (audio_job.error or "")
