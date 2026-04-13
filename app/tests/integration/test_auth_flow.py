"""Integration tests for authentication endpoints.

Tests the login/register pages (GET returns HTML forms) and
the logout redirect behaviour.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestLoginPage:
    def test_login_page_renders(self):
        response = client.get("/login")
        assert response.status_code == 200
        assert "Login" in response.text

    def test_login_returns_html(self):
        response = client.get("/login")
        assert "text/html" in response.headers["content-type"]


class TestLogout:
    def test_logout_redirects_to_login(self):
        response = client.get("/logout", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["location"]

    def test_logout_clears_cookie(self):
        response = client.get("/logout", follow_redirects=False)
        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token" in set_cookie
