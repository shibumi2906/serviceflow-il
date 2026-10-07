"""Unit tests for the Phase 0 liveness endpoint."""

from fastapi.testclient import TestClient

from serviceflow.config import Settings
from serviceflow.main import app, create_app


def test_liveness_returns_ok() -> None:
    response = TestClient(app).get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_api_route_uses_error_contract() -> None:
    response = TestClient(app).get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert set(response.json()) == {"code", "message", "details", "request_id"}


def test_smoke_mode_exposes_only_health_without_database() -> None:
    smoke_app = create_app(Settings(app_mode="smoke", app_env="production"))
    client = TestClient(smoke_app)

    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {
        "status": "ok",
        "mode": "smoke",
    }
    assert client.get("/api/v1/requests").status_code == 404
    assert client.get("/docs").status_code == 404
