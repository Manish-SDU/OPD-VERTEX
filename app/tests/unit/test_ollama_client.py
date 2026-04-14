"""Unit tests for the low-level Ollama client."""

from __future__ import annotations

import httpx
import pytest

from app.infrastructure.ai.llm.ollama_client import OllamaClient, OllamaClientError


def build_client(handler) -> OllamaClient:
    client = OllamaClient(
        base_url="http://ollama.local",
        model_name="qwen3:8b",
        timeout_seconds=5.0,
        max_retries=0,
    )
    client._client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://ollama.local",
        timeout=5.0,
    )
    return client


class TestOllamaClient:
    def test_generate_json_repairs_malformed_response(self):
        responses = iter(
            [
                '{"diagnosis":"Acute pharyngitis"',
                '{"diagnosis":"Acute pharyngitis","follow_up":"Not specified"}',
            ]
        )

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/generate"
            return httpx.Response(200, json={"response": next(responses)})

        client = build_client(handler)

        payload = client.generate_json(
            system_prompt="Return JSON only.",
            user_prompt="Generate report.",
            temperature=0.2,
            max_tokens=500,
        )

        assert payload["diagnosis"] == "Acute pharyngitis"
        assert payload["follow_up"] == "Not specified"

    def test_generate_json_raises_after_second_malformed_response(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/generate"
            return httpx.Response(200, json={"response": '{"diagnosis":"broken"'})

        client = build_client(handler)

        with pytest.raises(OllamaClientError, match="malformed JSON twice"):
            client.generate_json(
                system_prompt="Return JSON only.",
                user_prompt="Generate report.",
                temperature=0.2,
                max_tokens=500,
            )

    def test_check_status_handles_connection_failure(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused", request=request)

        client = build_client(handler)

        status = client.check_status()

        assert status.healthy is False
        assert status.ollama_reachable is False
        assert status.model_available is False
        assert "Ollama request failed" in status.detail

    def test_generate_json_raises_when_ollama_is_unavailable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused", request=request)

        client = build_client(handler)

        with pytest.raises(OllamaClientError, match="Ollama generation failed"):
            client.generate_json(
                system_prompt="Return JSON only.",
                user_prompt="Generate report.",
                temperature=0.2,
                max_tokens=500,
            )
