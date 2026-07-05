"""Three-stage AI pipeline (PRD 8).

summarize (concurrent, per article) -> outline -> script. Each stage returns its
structured Pydantic output plus accumulated token usage for cost capture. The
pipeline is pure orchestration over an injected ``LLMClient`` — no OpenAI import
here, so it is fully testable with a fake client (PRD 11.5).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.models import Length, Tone
from app.schemas.ai import ArticleSummary, EpisodeOutline, EpisodeScript
from app.schemas.news import Article
from app.services.ai import prompts
from app.services.ai.client import LLMClient


@dataclass
class PipelineResult:
    summaries: list[ArticleSummary]
    outline: EpisodeOutline
    script: EpisodeScript
    input_tokens: int = 0
    output_tokens: int = 0
    # Per-stage token usage for the analytics tiles / GenerationJob rows.
    stage_tokens: dict[str, int] = field(default_factory=dict)


async def summarize_articles(
    client: LLMClient, articles: list[Article]
) -> tuple[list[ArticleSummary], int, int]:
    """Stage 1: summarize each article concurrently."""

    async def _one(article: Article):
        return await client.structured_completion(
            system=prompts.SUMMARIZE_SYSTEM,
            user=prompts.build_summarize_user(article),
            schema=ArticleSummary,
        )

    results = await asyncio.gather(*(_one(a) for a in articles))
    summaries = [r.parsed for r in results]  # type: ignore[misc]
    tin = sum(r.input_tokens for r in results)
    tout = sum(r.output_tokens for r in results)
    return summaries, tin, tout


async def build_outline(
    client: LLMClient, summaries: list[ArticleSummary]
) -> tuple[EpisodeOutline, int, int]:
    """Stage 2: episode outline."""
    res = await client.structured_completion(
        system=prompts.OUTLINE_SYSTEM,
        user=prompts.build_outline_user(summaries),
        schema=EpisodeOutline,
    )
    return res.parsed, res.input_tokens, res.output_tokens  # type: ignore[return-value]


async def build_script(
    client: LLMClient,
    outline: EpisodeOutline,
    summaries: list[ArticleSummary],
    *,
    tone: Tone,
    length: Length,
    listener_name: str,
) -> tuple[EpisodeScript, int, int]:
    """Stage 3: final narration script."""
    res = await client.structured_completion(
        system=prompts.SCRIPT_SYSTEM,
        user=prompts.build_script_user(
            outline, summaries, tone=tone, length=length, listener_name=listener_name
        ),
        schema=EpisodeScript,
    )
    return res.parsed, res.input_tokens, res.output_tokens  # type: ignore[return-value]


async def run_pipeline(
    client: LLMClient,
    articles: list[Article],
    *,
    tone: Tone,
    length: Length,
    listener_name: str,
) -> PipelineResult:
    """Run all three stages end-to-end."""
    summaries, s_in, s_out = await summarize_articles(client, articles)
    outline, o_in, o_out = await build_outline(client, summaries)
    script, c_in, c_out = await build_script(
        client, outline, summaries, tone=tone, length=length, listener_name=listener_name
    )
    return PipelineResult(
        summaries=summaries,
        outline=outline,
        script=script,
        input_tokens=s_in + o_in + c_in,
        output_tokens=s_out + o_out + c_out,
        stage_tokens={
            "summarize": s_in + s_out,
            "outline": o_in + o_out,
            "script": c_in + c_out,
        },
    )
