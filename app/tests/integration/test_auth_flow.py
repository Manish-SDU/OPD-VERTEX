"""Integration tests for authentication endpoints."""

from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.core.security import ALGORITHM, SECRET_KEY

client = TestClient(app)


def _doctor_cookie() -> dict[str, str]:
    token = jwt.encode({"sub": "1", "role": "doctor"}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token}


class TestLoginPage:
    def test_login_page_renders(self):
        response = client.get("/login")
        assert response.status_code == 200
        assert "Login" in response.text

    def test_login_returns_html(self):
        response = client.get("/login")
        assert "text/html" in response.headers["content-type"]

    def test_root_redirects_to_login_when_unauthenticated(self):
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"


class TestLogout:
    def test_logout_redirects_to_login(self):
        response = client.get("/logout", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["location"]

    def test_logout_clears_cookie(self):
        response = client.get("/logout", follow_redirects=False)
        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token" in set_cookie


class TestConsultationCreate:
    def test_doctor_can_create_consultation(self):
        response = client.post(
            "/consultations",
            cookies=_doctor_cookie(),
            data={"patient_id": "1", "chief_complaint": "Headache"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"].startswith("/consultations/")

    def test_profile_page_loads_for_doctor(self):
        response = client.get("/profile", cookies=_doctor_cookie())
        assert response.status_code == 200
        assert "Ada" in response.text
