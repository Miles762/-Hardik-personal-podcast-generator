"""Test doubles: a fake LLM client and fake news service (PRD 11.5).

The fake LLM returns schema-valid structured outputs deterministically, so the
whole pipeline + /api/generate run offline with zero credits.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel

from app.schemas.ai import ArticleSummary, EpisodeOutline, EpisodeScript, OutlineSegment
from app.schemas.news import Article, RankedArticle
from app.services.ai.client import LLMResult
from app.services.news.service import NewsService


class FakeLLMClient:
    """Deterministic structured-output client. Records how many calls it got."""

    def __init__(self) -> None:
        self.calls = 0

    async def structured_completion(self, *, system: str, user: str, schema: type[BaseModel]) -> LLMResult:
        self.calls += 1
        if schema is ArticleSummary:
            parsed: BaseModel = ArticleSummary(
                title="Summarized headline", summary="A grounded summary.", importance=7
            )
        elif schema is EpisodeOutline:
            parsed = EpisodeOutline(
                segments=[
                    OutlineSegment(kind="opening", beat="Welcome"),
                    OutlineSegment(kind="story", reference="Summarized headline", beat="Story one"),
                    OutlineSegment(kind="closing", beat="Goodbye"),
                ]
            )
        elif schema is EpisodeScript:
            parsed = EpisodeScript(
                title="Your Daily Briefing",
                script="Hello and welcome. Here is your news. Thanks for listening.",
            )
        else:  # pragma: no cover - defensive
            raise AssertionError(f"unexpected schema {schema}")
        return LLMResult(parsed=parsed, input_tokens=100, output_tokens=50)


class FailingLLMClient:
    """Always raises — used to prove a stage fails cleanly into GenerationJob."""

    async def structured_completion(self, *, system: str, user: str, schema: type[BaseModel]) -> LLMResult:
        raise RuntimeError("openai boom")


class FakeTTSClient:
    """Returns deterministic fake MP3 bytes per chunk; records stitching hints."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def synthesize(self, text, *, voice_id, previous_text="", next_text=""):
        self.calls.append(
            {"text": text, "voice_id": voice_id,
             "previous_text": previous_text, "next_text": next_text}
        )
        # Minimal fake MP3-ish payload; merge is monkeypatched in service tests.
        return b"ID3" + text.encode()[:32].ljust(32, b"\x00")


class FakeStorage:
    """In-memory storage double; returns a public URL path."""

    def __init__(self) -> None:
        self.saved: dict[str, bytes] = {}

    async def save(self, filename: str, data: bytes) -> str:
        self.saved[filename] = data
        return f"/audio/{filename}"


def make_fake_news_service(n: int = 3) -> NewsService:
    """A NewsService whose get_ranked returns n static ranked articles (no network)."""

    class _Fake(NewsService):
        async def get_ranked(self, interests, length, *, weights=None, enrich=True):
            arts = [
                RankedArticle(
                    article=Article(
                        title=f"Story {i}",
                        source="BBC",
                        url=f"https://x.com/{i}",
                        published_at=datetime.now(UTC),
                        content=f"body text {i}",
                    ),
                    score=1.0 - i * 0.1,
                    subscores={},
                )
                for i in range(n)
            ]
            return arts, False

    return _Fake(providers=[])
