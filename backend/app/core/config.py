"""Application configuration, loaded from environment variables.

Kept intentionally small in Phase 0: only what is needed to boot the app and
connect to Postgres. Later phases extend this (OpenAI, ElevenLabs, ranking
weights, cost constants) without changing the loading mechanism.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings.

    Values come from environment variables (see ``.env.example``). Server-side
    only — API keys never reach the client (PRD 11.3).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Personalized Podcast Generator"
    environment: str = Field(default="development")

    # Database — async SQLAlchemy URL. Defaults to the docker-compose service.
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@db:5432/podcast",
    )

    # CORS: the Next.js frontend origin(s), comma-separated.
    cors_origins: str = Field(default="http://localhost:3000")

    # External APIs (server-side only). Empty in tests — clients are mocked.
    openai_api_key: str = Field(default="")
    elevenlabs_api_key: str = Field(default="")

    # AI models (PRD 8). Cheap multi-stage models by default.
    openai_model: str = Field(default="gpt-5-mini")

    # Per-episode hard timeout in seconds (PRD 4.2).
    generation_timeout_sec: int = Field(default=300)

    # In-process APScheduler (PRD 4.3). Disabled in tests.
    enable_scheduler: bool = Field(default=True)

    # Retry policy for external calls (PRD 11.1).
    max_retries: int = Field(default=3)
    retry_base_delay_sec: float = Field(default=0.5)

    # Rate limit on the generate endpoint (PRD 11.3): max requests per window.
    generate_rate_limit: int = Field(default=10)
    generate_rate_window_sec: int = Field(default=60)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (single source of config truth)."""
    return Settings()
