"""Integration tests for review workflow API endpoints.

These endpoints return JSON and don't require template rendering,
making them suitable for integration testing.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestReviewApproveEndpoint:
    def test_approve_returns_json(self):
        response = client.post("/review/1/approve")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "approved"
        assert body["consultation_id"] == "1"

    def test_approve_different_id(self):
        response = client.post("/review/99/approve")
        assert response.status_code == 200
        assert response.json()["consultation_id"] == "99"


class TestReviewRejectEndpoint:
    def test_reject_returns_json(self):
        response = client.post("/review/1/reject")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "rejected"
        assert body["consultation_id"] == "1"

    def test_reject_different_id(self):
        response = client.post("/review/42/reject")
        assert response.status_code == 200
        assert response.json()["consultation_id"] == "42"
