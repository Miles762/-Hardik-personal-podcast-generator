"""TTS client interface + ElevenLabs implementation (PRD 9, 11.5).

The audio service depends on the ``TTSClient`` Protocol, never on ElevenLabs
directly, so tests inject a fake that returns bytes without spending credits.
The real client uses request-stitching (previous_text / next_text) so prosody
flows across chunk seams (PRD 9).
"""

from __future__ import annotations

from typing import Protocol

import httpx

from app.core.retry import with_retry

ELEVEN_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
DEFAULT_MODEL = "eleven_multilingual_v2"


class TTSClient(Protocol):
    async def synthesize(
        self,
        text: str,
        *,
        voice_id: str,
        previous_text: str = "",
        next_text: str = "",
    ) -> bytes: ...


class ElevenLabsClient:
    """Real ElevenLabs TTS via HTTP. Returns MP3 bytes for one chunk."""

    def __init__(self, api_key: str, *, model: str = DEFAULT_MODEL, timeout: float = 60.0) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    async def synthesize(
        self,
        text: str,
        *,
        voice_id: str,
        previous_text: str = "",
        next_text: str = "",
    ) -> bytes:
        payload: dict = {
            "text": text,
            "model_id": self._model,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        # Request-stitching for prosody continuity across chunks (PRD 9).
        if previous_text:
            payload["previous_text"] = previous_text
        if next_text:
            payload["next_text"] = next_text

        async def _call() -> bytes:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    ELEVEN_TTS_URL.format(voice_id=voice_id),
                    headers={
                        "xi-api-key": self._api_key,
                        "accept": "audio/mpeg",
                        "content-type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                return resp.content

        # Exponential backoff on transient ElevenLabs failures (PRD 11.1).
        return await with_retry(_call, label="elevenlabs.tts")
