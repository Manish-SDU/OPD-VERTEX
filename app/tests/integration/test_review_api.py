"""Integration tests for review workflow API endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestReviewEndpoints:
    def test_approve_returns_json(self):
        response = client.post("/review/1/approve")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "approved"
        assert body["consultation_id"] == 1
        assert body["prescription_id"] is not None

    def test_reject_returns_json(self):
        response = client.post("/review/1/reject")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "rejected"
        assert body["consultation_id"] == 1

    def test_generate_report_requires_transcript(self):
        response = client.post("/review/2/generate-report")
        assert response.status_code == 400

    def test_llm_health_endpoint_exists(self):
        response = client.get("/llm/health")
        assert response.status_code == 200
        body = response.json()
        assert "healthy" in body
        assert "model_name" in body
