"""Ollama HTTP client — sync health check + async JSON generation."""

from __future__ import annotations

import json
import logging
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.domain.clinical_notes.models import LlmHealthStatus

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class OllamaClientError(RuntimeError):
    """Raised when the Ollama server cannot satisfy a request."""


class AsyncOllamaClient:
    """Async client using /api/chat with native JSON mode + Pydantic validation."""

    def __init__(
        self,
        base_url: str,
        model: str,
        temperature: float = 0.2,
        num_ctx: int = 8192,
        timeout_s: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.timeout_s = timeout_s

    def check_status(self) -> LlmHealthStatus:
        """Synchronous health check (used by the /llm/health endpoint)."""
        detail = ""
        ollama_reachable = False
        model_available = False
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
            ollama_reachable = True
            payload = response.json()
            models = payload.get("models", [])
            model_names = {
                item.get("name") or item.get("model") or ""
                for item in models
                if isinstance(item, dict)
            }
            model_available = self.model in model_names
            if not model_available:
                detail = f"Configured model '{self.model}' is not available in Ollama."
        except httpx.HTTPError as exc:
            detail = f"Ollama request failed: {exc}"

        return LlmHealthStatus(
            base_url=self.base_url,
            model_name=self.model,
            ollama_reachable=ollama_reachable,
            model_available=model_available,
            healthy=ollama_reachable and model_available,
            detail=detail,
        )

    async def _chat(self, system: str, user: str, temperature: float) -> str:
        body = {
            "model": self.model,
            "format": "json",
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": self.num_ctx},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            r = await client.post(f"{self.base_url}/api/chat", json=body)
            r.raise_for_status()
            payload = r.json()
        return payload["message"]["content"]

    async def generate_json(
        self,
        system: str,
        user: str,
        schema: type[T],
        retries: int = 1,
        temperature: float | None = None,
    ) -> T:
        """Call Ollama and validate the response against a Pydantic schema.

        On validation failure the error is fed back to the LLM so it can
        self-correct within `retries` additional attempts.
        """
        temp = self.temperature if temperature is None else temperature
        last_err: Exception | None = None
        prompt = user
        for attempt in range(retries + 1):
            try:
                raw = await self._chat(system, prompt, temp)
                data = json.loads(raw)
                return schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_err = exc
                log.warning(
                    "LLM JSON parse/validation failed (attempt %d): %s", attempt + 1, exc
                )
                prompt = (
                    f"{user}\n\n---\nYour previous response failed validation:\n{exc}\n"
                    "Return ONLY valid JSON conforming to the schema."
                )
        raise OllamaClientError(
            f"LLM produced no valid JSON after {retries + 1} attempts: {last_err}"
        )


class OllamaClient(AsyncOllamaClient):
    """Backward-compatible sync wrapper around AsyncOllamaClient.

    The review / clinical-notes pipeline is synchronous so it calls the old
    generate_json(system_prompt=, user_prompt=, temperature=, max_tokens=)
    interface, which this class restores using a blocking httpx call.
    """

    def generate_json(  # type: ignore[override]
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> dict:
        body = {
            "model": self.model,
            "format": "json",
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": max(self.num_ctx, max_tokens)},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        with httpx.Client(timeout=self.timeout_s) as client:
            r = client.post(f"{self.base_url}/api/chat", json=body)
            r.raise_for_status()
        content = r.json()["message"]["content"]
        import json as _json
        return _json.loads(content)
