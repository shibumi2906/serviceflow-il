"""Unit tests for the Phase 0 liveness endpoint."""

from fastapi.testclient import TestClient

from serviceflow.main import app


def test_liveness_returns_ok() -> None:
    response = TestClient(app).get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_api_route_uses_error_contract() -> None:
    response = TestClient(app).get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert set(response.json()) == {"code", "message", "details", "request_id"}
