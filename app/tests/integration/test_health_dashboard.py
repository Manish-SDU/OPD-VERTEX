from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_page() -> None:
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Recent Audit Events" in response.text
