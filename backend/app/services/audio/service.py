"""Audio service orchestrator (PRD 9).

script -> chunk -> sequential TTS (with request-stitching) -> merge -> store.
Sequential TTS by default (PRD 9): the user never waits on it (202 + poll). The
service depends on injected TTSClient + AudioStorage, so it is fully testable
offline with a fake that returns bytes (PRD 11.5).
"""

from __future__ import annotations

import logging

from app.services.audio.chunk import chunk_script
from app.services.audio.merge import merge_audio
from app.services.audio.storage import AudioStorage, LocalAudioStorage
from app.services.audio.tts import TTSClient

logger = logging.getLogger(__name__)


class AudioService:
    def __init__(self, tts: TTSClient, *, storage: AudioStorage | None = None) -> None:
        self._tts = tts
        self._storage = storage or LocalAudioStorage()

    async def synthesize_episode(
        self, script: str, *, voice_id: str, filename: str
    ) -> tuple[str, int]:
        """Return (audio_url, duration_sec) for the full episode."""
        chunks = chunk_script(script)
        if not chunks:
            raise ValueError("empty script; nothing to synthesize")

        audio_parts: list[bytes] = []
        # Sequential by default (PRD 9). Stitching passes neighbor text for prosody.
        for chunk in chunks:
            audio = await self._tts.synthesize(
                chunk.text,
                voice_id=voice_id,
                previous_text=chunk.previous_text,
                next_text=chunk.next_text,
            )
            audio_parts.append(audio)

        merged, duration = await merge_audio(audio_parts)
        url = await self._storage.save(filename, merged)
        logger.info("audio ready: %s (%ds, %d chunks)", url, duration, len(chunks))
        return url, duration
