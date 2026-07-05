"""SQLAlchemy 2.0 ORM models (PRD 5).

Design notes:
- ``Episode`` allows multiple rows per (user, date): the original UNIQUE
  constraint was dropped (migration e760b717b67f) when multiple manual episodes
  per day became a feature. The scheduler keeps once-a-day behavior by checking
  for an existing episode before inserting.
- Enum columns store the StrEnum *value* as text for portability.
- ``schedule`` is a nullable time-of-day string ("HH:MM") or NULL for "off".
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import EpisodeStatus, JobStatus, Length, Tone, Voice


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    preference: Mapped[Preference | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    episodes: Mapped[list[Episode]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Preference(Base):
    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    # List of interest strings; JSON keeps it portable (works on SQLite tests too).
    interests: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    voice: Mapped[Voice] = mapped_column(String(32), nullable=False, default=Voice.RACHEL)
    tone: Mapped[Tone] = mapped_column(String(32), nullable=False, default=Tone.PROFESSIONAL)
    podcast_length: Mapped[Length] = mapped_column(
        String(16), nullable=False, default=Length.MEDIUM
    )
    # "HH:MM" local time to generate daily, or NULL for "off" (PRD 4.3).
    schedule: Mapped[str | None] = mapped_column(String(5), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="preference")


class Episode(Base):
    __tablename__ = "episodes"
    # Revision (user-requested): multiple episodes per day are allowed, so the
    # former UNIQUE (user_id, episode_date) constraint was removed (PRD 5, 6).

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    episode_date: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    script: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[EpisodeStatus] = mapped_column(
        String(16), nullable=False, default=EpisodeStatus.PENDING
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="episodes")
    stories: Mapped[list[Story]] = relationship(
        back_populates="episode", cascade="all, delete-orphan"
    )
    play_events: Mapped[list[PlayEvent]] = relationship(
        back_populates="episode", cascade="all, delete-orphan"
    )
    jobs: Mapped[list[GenerationJob]] = relationship(
        back_populates="episode", cascade="all, delete-orphan"
    )


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    headline: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    importance: Mapped[int | None] = mapped_column(Integer, nullable=True)

    episode: Mapped[Episode] = relationship(back_populates="stories")


class PlayEvent(Base):
    __tablename__ = "play_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    episode: Mapped[Episode] = relationship(back_populates="play_events")


class Analytics(Base):
    """Seeded/mocked daily aggregates for the internal dashboard (PRD 10, 11.6)."""

    __tablename__ = "analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    active_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    episodes_generated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_listen_time_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class GenerationJob(Base):
    """Per-stage generation record — powers /status, progress, failed-jobs (PRD 4.2)."""

    __tablename__ = "generation_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        String(16), nullable=False, default=JobStatus.PENDING
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Observability fields (PRD 11.6): filled by later phases.
    tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    episode: Mapped[Episode] = relationship(back_populates="jobs")
