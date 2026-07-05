"""FastAPI application entrypoint.

Minimal wiring only — business logic lives in services (PRD 4 guiding principle).
CORS is locked to the frontend origin (PRD 11.3). On startup a lifespan hook
sweeps orphaned episodes left by a crash/restart (PRD 4.2).
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import dashboard, episodes, generate, health, news, preferences
from app.core.config import get_settings
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.services.audio.storage import AUDIO_DIR


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: recover any episode stuck by a crash/restart (PRD 4.2), then start
    # the in-process scheduler (PRD 4.3). Neither should block startup on failure.
    from app.services.generation.runner import sweep_orphaned_episodes
    from app.services.scheduler.scheduler import shutdown_scheduler, start_scheduler

    try:
        await sweep_orphaned_episodes()
    except Exception:  # noqa: BLE001
        pass
    try:
        if get_settings().enable_scheduler:
            await start_scheduler()
    except Exception:  # noqa: BLE001
        pass
    yield
    shutdown_scheduler()


def _install_error_handlers(app: FastAPI) -> None:
    """Consistent JSON error envelope {error: {code, message}} (PRD 6)."""

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.status_code, "message": exc.detail}},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exc(request: Request, exc: RequestValidationError):
        from fastapi.encoders import jsonable_encoder

        return JSONResponse(
            status_code=422,
            content={"error": {"code": 422, "message": "Validation error",
                               "details": jsonable_encoder(exc.errors())}},
        )


def create_app() -> FastAPI:
    """Application factory. Keeps wiring testable and import-side-effect free."""
    settings = get_settings()
    configure_logging()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _install_error_handlers(app)

    # Routers. More are mounted in later phases (preferences, dashboard, ...).
    app.include_router(health.router, prefix="/api")
    app.include_router(news.router, prefix="/api")
    app.include_router(generate.router, prefix="/api")
    app.include_router(episodes.router, prefix="/api")
    app.include_router(preferences.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")

    # Serve generated MP3s. StaticFiles supports HTTP Range requests, so the
    # player can seek (PRD 9). CORS middleware above adds headers for the
    # frontend origin; the download button uses the Next /audio rewrite proxy.
    Path(AUDIO_DIR).mkdir(parents=True, exist_ok=True)
    app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

    return app


app = create_app()
