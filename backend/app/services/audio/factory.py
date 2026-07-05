"""Audio factory + orchestrator hook (PRD 9).

`build_audio_hook()` returns the async callable the orchestrator invokes to turn
a finished script into a stored MP3. It resolves the episode owner's voice
preference to an ElevenLabs voice id and delegates to AudioService. Kept out of
the orchestrator so the ElevenLabs SDK/key never load in tests.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models import VOICE_IDS, Episode, User, Voice
from app.services.audio.service import AudioService
from app.services.audio.tts import ElevenLabsClient


def build_audio_service() -> AudioService:
    settings = get_settings()
    if not settings.elevenlabs_api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set; cannot build TTS client.")
    return AudioService(ElevenLabsClient(api_key=settings.elevenlabs_api_key))


async def _resolve_voice_id(session: AsyncSession, user_id: int) -> str:
    user = (
        await session.execute(
            select(User).options(selectinload(User.preference)).where(User.id == user_id)
        )
    ).scalar_one()
    pref = user.preference
    voice = Voice(pref.voice) if pref else Voice.RACHEL
    return VOICE_IDS[voice]


def build_audio_hook(session: AsyncSession):
    """Return an async (episode, script) -> (audio_url, duration_sec) hook."""
    service = build_audio_service()

    async def _hook(episode: Episode, script: str) -> tuple[str, int]:
        voice_id = await _resolve_voice_id(session, episode.user_id)
        filename = f"episode_{episode.id}.mp3"
        return await service.synthesize_episode(
            script, voice_id=voice_id, filename=filename
        )

    return _hook
