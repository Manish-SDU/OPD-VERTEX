"""Integration tests for request logging middleware.

Verifies that the middleware logs requests without breaking the
response pipeline.
"""

import logging

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestRequestLoggingMiddleware:
    def test_middleware_does_not_break_response(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_middleware_logs_request(self, caplog):
        with caplog.at_level(logging.INFO, logger="opd_vertex.middleware.request"):
            client.get("/health")

        messages = [r.message for r in caplog.records]
        assert any("[REQUEST]" in m and "/health" in m for m in messages)

    def test_middleware_logs_response(self, caplog):
        with caplog.at_level(logging.INFO, logger="opd_vertex.middleware.request"):
            client.get("/health")

        messages = [r.message for r in caplog.records]
        assert any("[RESPONSE]" in m and "200" in m for m in messages)

    def test_middleware_on_404(self, caplog):
        with caplog.at_level(logging.INFO, logger="opd_vertex.middleware.request"):
            response = client.get("/nonexistent-route-xyz")

        assert response.status_code == 404
        messages = [r.message for r in caplog.records]
        assert any("[RESPONSE]" in m and "404" in m for m in messages)
