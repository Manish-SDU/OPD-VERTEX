"""Unit tests for AsyncOllamaClient."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio
from pydantic import BaseModel

from app.infrastructure.ai.llm.ollama_client import AsyncOllamaClient, OllamaClientError


class _Report(BaseModel):
    diagnosis: str
    follow_up: str = ""


def _chat_response(content: str) -> dict:
    return {"message": {"role": "assistant", "content": content}}


def _make_client(transport: httpx.MockTransport) -> AsyncOllamaClient:
    client = AsyncOllamaClient(
        base_url="http://ollama.local",
        model="llama3.1:8b",
        timeout_s=5.0,
    )
    # Patch the internal AsyncClient used by _chat
    client._transport = transport
    return client


class TestAsyncOllamaClient:
    @pytest.mark.asyncio
    async def test_valid_json_returns_model(self):
        payload = json.dumps({"diagnosis": "Acute pharyngitis", "follow_up": "1 week"})

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/chat"
            return httpx.Response(200, json=_chat_response(payload))

        client = AsyncOllamaClient(
            base_url="http://ollama.local", model="llama3.1:8b", timeout_s=5.0
        )

        async def _patched_chat(system, user, temperature):
            return payload

        client._chat = _patched_chat
        result = await client.generate_json("sys", "user", _Report)
        assert result.diagnosis == "Acute pharyngitis"
        assert result.follow_up == "1 week"

    @pytest.mark.asyncio
    async def test_invalid_json_retries_and_succeeds(self):
        responses = iter([
            '{"diagnosis":"Acute pharyngitis"',  # missing closing brace — invalid JSON
            '{"diagnosis":"Acute pharyngitis","follow_up":"None"}',
        ])

        async def _patched_chat(system, user, temperature):
            return next(responses)

        client = AsyncOllamaClient(
            base_url="http://ollama.local", model="llama3.1:8b", timeout_s=5.0
        )
        client._chat = _patched_chat

        result = await client.generate_json("sys", "user", _Report, retries=1)
        assert result.diagnosis == "Acute pharyngitis"

    @pytest.mark.asyncio
    async def test_two_failures_raises_error(self):
        async def _patched_chat(system, user, temperature):
            return '{"bad json'

        client = AsyncOllamaClient(
            base_url="http://ollama.local", model="llama3.1:8b", timeout_s=5.0
        )
        client._chat = _patched_chat

        with pytest.raises(OllamaClientError):
            await client.generate_json("sys", "user", _Report, retries=1)

    def test_check_status_handles_connection_failure(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused", request=request)

        client = AsyncOllamaClient(
            base_url="http://ollama.local", model="llama3.1:8b", timeout_s=5.0
        )
        # Inject mock transport into a sync httpx.Client for the health check
        with httpx.Client(transport=httpx.MockTransport(handler)) as _:
            pass  # just verifying mock works; check_status uses its own client

        status = client.check_status()
        assert status.healthy is False
        assert status.ollama_reachable is False
        assert "Ollama request failed" in status.detail
