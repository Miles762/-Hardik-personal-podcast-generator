"""Shared pytest fixtures.

An in-memory SQLite async database gives fast, deterministic, credit-free tests
(PRD 11.5). The models use portable column types (JSON, String enums) so the same
schema that runs on Postgres also creates cleanly on SQLite.
"""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Disable the in-process scheduler for all tests before settings are read
# (PRD 4.3) — tests must not start a real event-loop scheduler.
os.environ.setdefault("ENABLE_SCHEDULER", "false")

import app.models  # noqa: E402,F401  (register models on Base.metadata)
from app.db.base import Base  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """Ensure each test sees fresh, env-driven settings."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an isolated in-memory async session with a fresh schema per test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session

    await engine.dispose()
