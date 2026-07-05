"""Preferences router — GET + PATCH /api/preferences (PRD 6, 10).

PATCH backs both onboarding save and the settings page. Thin: validate + persist.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Preference, User
from app.schemas.preference import PreferenceOut, PreferenceUpdate
from app.services.scheduler.scheduler import register_user_job

router = APIRouter(tags=["preferences"])


def _to_out(user: User) -> PreferenceOut:
    pref = user.preference
    return PreferenceOut(
        name=user.name,
        interests=pref.interests if pref else [],
        voice=pref.voice if pref else "rachel",       # type: ignore[arg-type]
        tone=pref.tone if pref else "professional",   # type: ignore[arg-type]
        podcast_length=pref.podcast_length if pref else "medium",  # type: ignore[arg-type]
        schedule=pref.schedule if pref else None,
    )


@router.get("/preferences", response_model=PreferenceOut)
async def get_preferences(user: User = Depends(get_current_user)) -> PreferenceOut:
    return _to_out(user)


@router.patch("/preferences", response_model=PreferenceOut)
async def update_preferences(
    payload: PreferenceUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PreferenceOut:
    if payload.name is not None:
        user.name = payload.name

    pref = user.preference
    if pref is None:
        pref = Preference(user_id=user.id, interests=[])
        db.add(pref)
        user.preference = pref

    data = payload.model_dump(exclude_unset=True, exclude={"name"})
    for field, value in data.items():
        setattr(pref, field, value)

    await db.commit()
    await db.refresh(user)

    # Re-register the user's daily job so a schedule change takes effect (PRD 4.3).
    if get_settings().enable_scheduler:
        try:
            register_user_job(user.id, pref.schedule)
        except Exception:  # noqa: BLE001 — scheduler issues must not fail the save
            pass

    return _to_out(user)
