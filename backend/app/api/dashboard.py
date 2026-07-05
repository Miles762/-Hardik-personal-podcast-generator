"""Dashboard router — GET /api/dashboard (PRD 6, 10, 11.6). Thin: delegates."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.dashboard import DashboardResponse
from app.services.analytics.service import build_dashboard

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(db: AsyncSession = Depends(get_db)) -> DashboardResponse:
    return await build_dashboard(db)
