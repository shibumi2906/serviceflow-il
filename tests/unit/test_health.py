"""Unit tests for the Phase 0 liveness endpoint."""

from fastapi.testclient import TestClient

from serviceflow.main import app


def test_liveness_returns_ok() -> None:
    response = TestClient(app).get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
