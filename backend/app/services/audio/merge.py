"""Audio merge + duration (PRD 9).

pydub merging is CPU-bound and requires ffmpeg, so it runs in a threadpool
executor and never blocks the event loop. If ffmpeg is unavailable, we fall back
to concatenating the MP3 byte streams directly — valid for same-codec ElevenLabs
output (PRD 9 fallback).
"""

from __future__ import annotations

import asyncio
import io
import logging

logger = logging.getLogger(__name__)


def _merge_with_pydub(chunks: list[bytes]) -> tuple[bytes, int]:
    """Decode + concatenate via pydub; return (mp3_bytes, duration_seconds)."""
    from pydub import AudioSegment

    combined = AudioSegment.empty()
    for chunk in chunks:
        combined += AudioSegment.from_file(io.BytesIO(chunk), format="mp3")
    out = io.BytesIO()
    combined.export(out, format="mp3")
    return out.getvalue(), round(len(combined) / 1000)


def _merge_by_concat(chunks: list[bytes]) -> tuple[bytes, int]:
    """Fallback: byte-concat same-codec MP3s. Duration is estimated, not exact."""
    data = b"".join(chunks)
    # Rough estimate: ElevenLabs mp3_44100_128 ≈ 16 KB/s.
    duration = round(len(data) / 16000)
    return data, duration


def merge_sync(chunks: list[bytes]) -> tuple[bytes, int]:
    """Merge chunk MP3s. Tries pydub (accurate), falls back to concat."""
    if not chunks:
        return b"", 0
    try:
        return _merge_with_pydub(chunks)
    except Exception as exc:  # noqa: BLE001 — ffmpeg missing / decode error
        logger.warning("pydub merge failed (%s); falling back to byte concat", exc)
        return _merge_by_concat(chunks)


async def merge_audio(chunks: list[bytes]) -> tuple[bytes, int]:
    """Async wrapper: run the CPU-bound merge in a threadpool (PRD 9)."""
    return await asyncio.get_running_loop().run_in_executor(None, merge_sync, chunks)
