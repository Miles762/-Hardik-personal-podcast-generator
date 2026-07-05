"""Health check router.

Phase 0 deliverable: a liveness endpoint that proves the scaffold boots. Used by
the docker-compose healthcheck so the frontend waits for a ready backend.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe. Returns 200 when the app process is serving."""
    return {"status": "ok"}
