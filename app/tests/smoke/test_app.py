"""Smoke tests — verify the application boots and core routes respond.

These are fast, shallow checks that the app is wired correctly.
"""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_app_boots() -> None:
    """The app should instantiate without errors."""
    assert app.title == "MedFlow"


def test_health_reachable() -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_login_page_reachable() -> None:
    response = client.get("/login")
    assert response.status_code == 200


def test_static_css_mounted() -> None:
    """Static file mount should serve the app CSS."""
    response = client.get("/static/css/app.css")
    assert response.status_code == 200


def test_static_js_mounted() -> None:
    response = client.get("/static/js/app.js")
    assert response.status_code == 200


def test_openapi_schema_available() -> None:
    """FastAPI auto-generates an OpenAPI schema."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "MedFlow"
    assert "/health" in schema["paths"]
