"""Integration tests for review workflow API endpoints."""

from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.core.security import ALGORITHM, SECRET_KEY

client = TestClient(app)


def _doctor_cookie() -> dict[str, str]:
    token = jwt.encode({"sub": "1", "role": "doctor"}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token}


class TestReviewEndpoints:
    def test_review_page_uses_generate_report_endpoint(self):
        response = client.get("/review/4101", cookies=_doctor_cookie())
        assert response.status_code == 200
        assert "generate-report" in response.text

    def test_print_report_page_exists(self):
        response = client.get("/review/report/4101/print", cookies=_doctor_cookie())
        assert response.status_code == 200
        assert "Save as PDF / Print" in response.text
        assert "print-report-rendered" in response.text

    def test_generate_report_succeeds_for_seeded_demo_transcript(self):
        response = client.post("/review/4101/generate-report", cookies=_doctor_cookie())
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "generated"
        assert body["consultation_id"] == 4101

    def test_approve_returns_json(self):
        response = client.post("/review/1/approve", cookies=_doctor_cookie())
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "approved"
        assert body["consultation_id"] == 1
        assert body["prescription_id"] is not None

    def test_reject_returns_json(self):
        response = client.post("/review/1/reject", cookies=_doctor_cookie())
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "rejected"
        assert body["consultation_id"] == 1

    def test_generate_report_requires_transcript(self):
        response = client.post("/review/2/generate-report", cookies=_doctor_cookie())
        assert response.status_code == 400

    def test_llm_health_endpoint_exists(self):
        response = client.get("/llm/health")
        assert response.status_code == 200
        body = response.json()
        assert "healthy" in body
        assert "model_name" in body
