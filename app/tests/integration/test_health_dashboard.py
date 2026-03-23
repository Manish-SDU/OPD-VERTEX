"""Integration tests for health and API-level endpoints.

These tests use FastAPI's TestClient to test the HTTP layer.
Only endpoints that don't require DB connections are tested here.
"""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mode"] == "mock"


def test_health_returns_json_content_type() -> None:
    response = client.get("/health")
    assert "application/json" in response.headers["content-type"]
