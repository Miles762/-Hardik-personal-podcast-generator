"""Async database engine and session factory + FastAPI dependency.

One engine per process; sessions are per-request via ``get_db`` (dependency
injection, PRD 11.4). The engine URL comes from settings (PRD 11.3).
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped async session; commit/rollback handled by caller."""
    async with SessionLocal() as session:
        yield session
