"""SQLAlchemy declarative base and shared column helpers.

All ORM models inherit from ``Base``. Kept separate from the session so Alembic
can import metadata without pulling in the engine.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all models."""


def utcnow_column() -> Mapped[datetime]:
    """A timezone-aware ``created_at``-style column defaulting to server now()."""
    return mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
