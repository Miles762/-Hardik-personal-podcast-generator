"""MP3 storage (PRD 9, 12.6).

Storage-agnostic interface so prod can swap local disk for S3/GCS. The local
implementation writes under the static audio dir; the returned ``audio_url`` is
the path the StaticFiles mount serves (with HTTP Range support for seeking).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

# Served at /audio/<name> via the StaticFiles mount (see main.py).
AUDIO_DIR = Path("static/audio")
AUDIO_URL_PREFIX = "/audio"


class AudioStorage(Protocol):
    async def save(self, filename: str, data: bytes) -> str: ...


class LocalAudioStorage:
    """Write MP3s to the local static dir. Returns the public URL path."""

    def __init__(self, base_dir: Path = AUDIO_DIR) -> None:
        self._base = base_dir

    async def save(self, filename: str, data: bytes) -> str:
        self._base.mkdir(parents=True, exist_ok=True)
        path = self._base / filename
        path.write_bytes(data)
        return f"{AUDIO_URL_PREFIX}/{filename}"
