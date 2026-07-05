"""LLM client factory (PRD 8, 11.3).

Builds the real OpenAI client from settings. Kept separate so the orchestrator
imports a factory, not the SDK — tests pass a fake client and never touch this.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.services.ai.client import LLMClient, OpenAIClient


def build_llm_client() -> LLMClient:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set; cannot build OpenAI client.")
    return OpenAIClient(api_key=settings.openai_api_key, model=settings.openai_model)
