"""Domain enums shared by SQLAlchemy models and Pydantic schemas (PRD 5).

Single source of truth for Tone, Voice, Length, Schedule, and lifecycle status
values. Stored as strings in Postgres (portable, human-readable in the DB).
"""

from enum import StrEnum


class Tone(StrEnum):
    """Narration tone; steers the Stage 3 script prompt (PRD 8)."""

    CALM = "calm"
    ENERGETIC = "energetic"
    PROFESSIONAL = "professional"
    WITTY = "witty"


class Voice(StrEnum):
    """Friendly voice names mapped to ElevenLabs voice IDs in VOICE_IDS (PRD 5, 9)."""

    RACHEL = "rachel"
    ADAM = "adam"
    BELLA = "bella"
    ANTONI = "antoni"


# Friendly name -> ElevenLabs voice id. Kept here so the audio service (Phase 4)
# resolves a preference to a concrete voice without hardcoding ids elsewhere.
# These are ElevenLabs' well-known default community voice ids.
VOICE_IDS: dict[Voice, str] = {
    Voice.RACHEL: "21m00Tcm4TlvDq8ikWAM",
    Voice.ADAM: "pNInz6obpgDQGcFmaJgB",
    Voice.BELLA: "EXAVITQu4vr4xnSDxMaL",
    Voice.ANTONI: "ErXwobaYiN019PkySvjV",
}


class Length(StrEnum):
    """Podcast length preset. Drives top-N story count and target word count."""

    SHORT = "short"    # ~3 min
    MEDIUM = "medium"  # ~6 min
    LONG = "long"      # ~10 min


# Length -> (approx target minutes, number of stories fed to the LLM). N per PRD 7.
LENGTH_MINUTES: dict[Length, int] = {
    Length.SHORT: 3,
    Length.MEDIUM: 6,
    Length.LONG: 10,
}
LENGTH_STORY_COUNT: dict[Length, int] = {
    Length.SHORT: 3,
    Length.MEDIUM: 5,
    Length.LONG: 8,
}


class EpisodeStatus(StrEnum):
    """Episode lifecycle (PRD 4.2 / 5)."""

    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class JobStatus(StrEnum):
    """Per-stage GenerationJob status (PRD 4.2, 11.6)."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
