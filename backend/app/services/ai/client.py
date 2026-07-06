"""LLM client interface + OpenAI implementation (PRD 8, 11.5).

The pipeline depends on the ``LLMClient`` Protocol, never on the OpenAI SDK
directly, so tests inject a fake and spend zero credits. The real client uses
OpenAI Structured Outputs (``response_format`` from a Pydantic model) so a stage
gets exactly its schema back or raises — no prompt-hoping (PRD 8).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.core.retry import with_retry

TModel = TypeVar("TModel", bound=BaseModel)


@dataclass
class LLMResult:
    """Parsed structured output plus token usage for cost/latency capture."""

    parsed: BaseModel
    input_tokens: int = 0
    output_tokens: int = 0


class LLMClient(Protocol):
    async def structured_completion(
        self,
        *,
        system: str,
        user: str,
        schema: type[BaseModel],
    ) -> LLMResult: ...


class OpenAIClient:
    """Real OpenAI-backed client using structured outputs + one retry."""

    def __init__(self, api_key: str, model: str) -> None:
        # Imported lazily so the module (and tests) load without the SDK/key.
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def structured_completion(
        self,
        *,
        system: str,
        user: str,
        schema: type[BaseModel],
    ) -> LLMResult:
        async def _call() -> LLMResult:
            completion = await self._client.beta.chat.completions.parse(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format=schema,
            )
            parsed = completion.choices[0].message.parsed
            if parsed is None:
                raise _MalformedResponse("model returned no parsed content")
            usage = completion.usage
            return LLMResult(
                parsed=parsed,
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            )

        # Retry transient API failures AND a malformed/empty model response
        # (a fresh call often parses cleanly); other errors surface immediately.
        return await with_retry(
            _call, label="openai.structured", retry_on=_ai_retryable
        )


class _MalformedResponse(Exception):
    """Raised when the model returns no parsable structured output."""


def _ai_retryable(exc: BaseException) -> bool:
    """Retry transient network/HTTP failures, OpenAI API errors, and a
    malformed model response — but not programming errors or bad input."""
    from app.core.retry import is_transient

    if isinstance(exc, _MalformedResponse):
        return True
    # OpenAI SDK transient errors (rate limit, timeout, connection, 5xx).
    try:
        from openai import (
            APIConnectionError,
            APITimeoutError,
            InternalServerError,
            RateLimitError,
        )

        if isinstance(
            exc,
            APIConnectionError | APITimeoutError | RateLimitError | InternalServerError,
        ):
            return True
    except ImportError:  # pragma: no cover - SDK always present at runtime
        pass
    return is_transient(exc)
