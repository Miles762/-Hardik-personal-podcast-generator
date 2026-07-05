"""Structured-output contracts for the 3-stage AI pipeline (PRD 8).

Each stage has a strict Pydantic model. These are handed to OpenAI Structured
Outputs (response_format = json_schema) so the model *must* return this shape;
a parse/schema failure is retried once then fails the stage cleanly (PRD 8).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ArticleSummary(BaseModel):
    """Stage 1 output — one per article."""

    title: str = Field(description="Concise, rewritten headline for narration.")
    summary: str = Field(description="2-4 sentence factual summary, grounded in the source.")
    importance: int = Field(ge=1, le=10, description="Editorial importance 1-10.")


class OutlineSegment(BaseModel):
    kind: str = Field(description="One of: opening, story, transition, closing.")
    reference: str = Field(
        default="",
        description="For 'story' segments, the title of the summarized story it covers.",
    )
    beat: str = Field(description="One line describing what this segment should say.")


class EpisodeOutline(BaseModel):
    """Stage 2 output — ordered segments opening -> ... -> closing."""

    segments: list[OutlineSegment]


class EpisodeScript(BaseModel):
    """Stage 3 output — the final narration."""

    title: str = Field(description="Catchy episode title.")
    script: str = Field(description="Full conversational narration, ready for TTS.")
