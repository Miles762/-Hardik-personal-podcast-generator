"""API schemas for preferences (PRD 6, 10)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.models import Length, Tone, Voice


class PreferenceOut(BaseModel):
    name: str
    interests: list[str]
    voice: Voice
    tone: Tone
    podcast_length: Length
    schedule: str | None


MAX_INTERESTS = 20
MAX_INTEREST_LENGTH = 100


class PreferenceUpdate(BaseModel):
    """Onboarding + settings save. All fields optional (partial update)."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    interests: list[str] | None = None
    voice: Voice | None = None
    tone: Tone | None = None
    podcast_length: Length | None = None
    # "HH:MM" 24h, or null for "off".
    schedule: str | None = None

    model_config = {"extra": "forbid"}  # reject unknown fields (PRD 6)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, v: str | None) -> str | None:
        """Collapse whitespace and reject blank names ("  " passes min_length)."""
        if v is None:
            return None
        cleaned = " ".join(v.split())
        if not cleaned:
            raise ValueError("name cannot be blank")
        return cleaned

    @field_validator("interests")
    @classmethod
    def _clean_interests(cls, v: list[str] | None) -> list[str] | None:
        """Trim, drop empties, dedupe case-insensitively, and cap size/length."""
        if v is None:
            return None
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in v:
            item = " ".join(raw.split())
            if not item:
                continue
            if len(item) > MAX_INTEREST_LENGTH:
                raise ValueError(
                    f"each interest must be at most {MAX_INTEREST_LENGTH} characters"
                )
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(item)
        if len(cleaned) > MAX_INTERESTS:
            raise ValueError(f"at most {MAX_INTERESTS} interests are allowed")
        return cleaned

    @field_validator("schedule")
    @classmethod
    def _valid_schedule(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        parts = v.split(":")
        if len(parts) != 2 or not (parts[0].isdigit() and parts[1].isdigit()):
            raise ValueError("schedule must be 'HH:MM' or null")
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError("schedule out of range")
        return f"{h:02d}:{m:02d}"
