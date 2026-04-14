"""Low-level Ollama HTTP client for local Qwen3 8B access."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from app.domain.clinical_notes.models import LlmHealthStatus


class OllamaClientError(RuntimeError):
    """Raised when the local Ollama server cannot satisfy a request."""


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        model_name: str,
        timeout_seconds: float = 120.0,
        max_retries: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._client = httpx.Client(
            base_url=self.base_url, timeout=self.timeout_seconds
        )

    def check_status(self) -> LlmHealthStatus:
        detail = ""
        ollama_reachable = False
        model_available = False
        try:
            response = self._client.get("/api/tags")
            response.raise_for_status()
            ollama_reachable = True
            payload = response.json()
            models = payload.get("models", [])
            model_names = {
                item.get("name") or item.get("model") or ""
                for item in models
                if isinstance(item, dict)
            }
            model_available = self.model_name in model_names
            if not model_available:
                detail = (
                    f"Configured model '{self.model_name}' is not available in Ollama."
                )
        except httpx.HTTPError as exc:
            detail = f"Ollama request failed: {exc}"

        return LlmHealthStatus(
            base_url=self.base_url,
            model_name=self.model_name,
            ollama_reachable=ollama_reachable,
            model_available=model_available,
            healthy=ollama_reachable and model_available,
            detail=detail,
        )

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        raw_response = self._generate_once(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        parsed = self._parse_json(raw_response)
        if parsed is not None:
            return parsed

        repaired_response = self._repair_json(
            raw_response=raw_response,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        repaired = self._parse_json(repaired_response)
        if repaired is None:
            raise OllamaClientError("Qwen3 returned malformed JSON twice.")
        return repaired

    def _generate_once(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        payload = {
            "model": self.model_name,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 2):
            try:
                response = self._client.post("/api/generate", json=payload)
                response.raise_for_status()
                body = response.json()
                text = body.get("response", "")
                if not text:
                    raise OllamaClientError("Ollama returned an empty response body.")
                return text
            except (httpx.HTTPError, OllamaClientError, ValueError) as exc:
                last_error = exc
                if attempt > self.max_retries:
                    break
                time.sleep(0.35 * attempt)

        raise OllamaClientError(f"Ollama generation failed: {last_error}")

    def _repair_json(
        self, *, raw_response: str, temperature: float, max_tokens: int
    ) -> str:
        repair_system_prompt = (
            "You repair malformed JSON. Return only valid JSON. "
            "Do not add commentary or new facts."
        )
        repair_user_prompt = (
            "Repair the following malformed JSON so it becomes valid JSON.\n"
            "Return only the repaired JSON object.\n\n"
            f"{raw_response}"
        )
        return self._generate_once(
            system_prompt=repair_system_prompt,
            user_prompt=repair_user_prompt,
            temperature=min(temperature, 0.1),
            max_tokens=max_tokens,
        )

    def _parse_json(self, raw_response: str) -> dict[str, Any] | None:
        candidate = self._extract_json_candidate(raw_response)
        if candidate is None:
            return None
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed

    def _extract_json_candidate(self, raw_response: str) -> str | None:
        stripped = raw_response.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped

        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return stripped[start : end + 1]
