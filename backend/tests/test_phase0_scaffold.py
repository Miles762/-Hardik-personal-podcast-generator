"""Phase 0 tests: prove the scaffold boots and serves health end-to-end.

Runs fully offline — no DB, no external APIs, no credit spend.
"""

from fastapi.testclient import TestClient

from app.main import create_app


def test_app_factory_builds() -> None:
    """The application factory returns a wired FastAPI app."""
    app = create_app()
    assert app.title == "Personalized Podcast Generator"


def test_health_endpoint_ok() -> None:
    """GET /api/health returns 200 with an ok status."""
    client = TestClient(create_app())
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_openapi_schema_available() -> None:
    """FastAPI emits an OpenAPI schema — the basis for the typed TS client (PRD 4)."""
    client = TestClient(create_app())
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert resp.json()["openapi"].startswith("3.")
