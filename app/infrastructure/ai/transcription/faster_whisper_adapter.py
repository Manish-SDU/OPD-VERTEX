"""Faster-Whisper API client - communicates with Whisper microservice."""

from __future__ import annotations

from logging import getLogger

import httpx

from app.core.config import get_settings
from app.domain.transcriptions.models import (
    StreamingTranscriptChunk,
    StreamingTranscriptionService,
    TranscriptResult,
    TranscriptionService,
)

logger = getLogger("opd_vertex.infrastructure.ai.transcription")


class FasterWhisperTranscriptionService(TranscriptionService):
    """Batch transcription service for complete audio files (via Whisper API)."""

    def __init__(self, model_size: str = "base", device: str = "cuda"):
        self.http_client = None
        self.whisper_api_url = get_settings().whisper_api_url

    def _get_client(self):
        """Lazy initialize HTTP client."""
        if self.http_client is None:
            self.http_client = httpx.Client(
                base_url=self.whisper_api_url,
                timeout=60.0,
            )
        return self.http_client

    def transcribe(self, audio_path: str) -> TranscriptResult:
        """Transcribe complete audio file."""
        raise NotImplementedError("Use StreamingFasterWhisperService instead")


class StreamingFasterWhisperService(StreamingTranscriptionService):
    """Streaming transcription service that calls the Whisper API microservice."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cuda",
        chunk_duration: float = 2.0,
        sample_rate: int = 16000,
    ):
        self.chunk_duration = chunk_duration
        self.sample_rate = sample_rate
        self.chunk_size = int(chunk_duration * sample_rate)
        self.http_client = None
        self.whisper_api_url = get_settings().whisper_api_url

    def _get_client(self):
        """Lazy initialize HTTP client."""
        if self.http_client is None:
            logger.debug(
                "Creating Whisper API client base_url=%s", self.whisper_api_url
            )
            self.http_client = httpx.Client(
                base_url=self.whisper_api_url,
                timeout=60.0,
            )
        return self.http_client

    def start_streaming(self, consultation_id: int) -> str:
        """Initialize a streaming session via Whisper API."""
        try:
            client = self._get_client()
            logger.debug(
                "Starting Whisper streaming session consultation_id=%s",
                consultation_id,
            )
            response = client.post(
                "/sessions/start",
                json={
                    "consultation_id": consultation_id,
                    "chunk_duration": self.chunk_duration,
                    "sample_rate": self.sample_rate,
                },
            )
            logger.debug(
                "Whisper start response consultation_id=%s status_code=%s",
                consultation_id,
                response.status_code,
            )
            response.raise_for_status()
            data = response.json()
            return data["session_id"]
        except Exception as exc:
            logger.exception(
                "Failed to start Whisper streaming consultation_id=%s error=%s",
                consultation_id,
                exc,
            )
            raise

    def add_audio_chunk(
        self, session_id: str, audio_bytes: bytes
    ) -> StreamingTranscriptChunk | None:
        """Add audio chunk via Whisper API."""
        try:
            client = self._get_client()
            response = client.post(
                f"/sessions/{session_id}/chunk",
                content=audio_bytes,
                headers={"Content-Type": "application/octet-stream"},
            )
            response.raise_for_status()

            try:
                chunk_data = response.json()
                if chunk_data:
                    return StreamingTranscriptChunk(
                        chunk_id=chunk_data["chunk_id"],
                        text=chunk_data["text"],
                        timestamp=chunk_data["timestamp"],
                        is_final=chunk_data.get("is_final", False),
                    )
            except Exception:
                pass

            return None
        except Exception as exc:
            logger.exception(
                "Failed to send audio chunk to Whisper session_id=%s error=%s",
                session_id,
                exc,
            )
            raise

    def get_completed_results(self, session_id: str) -> list[dict]:
        """Return empty list — live text is delivered via get_current_text / partial_text only.

        Returning cumulative text here would cause the frontend to append it to
        finalizedTranscript on every poll loop, producing duplicated transcript text.
        """
        return []

    def finalize_session(self, session_id: str) -> TranscriptResult:
        """End streaming and retrieve final transcription from Whisper API."""
        try:
            client = self._get_client()
            response = client.post(f"/sessions/{session_id}/complete")
            response.raise_for_status()
            data = response.json()

            return TranscriptResult(
                consultation_id=data["consultation_id"],
                file_path="",
                full_text=data["full_text"],
            )
        except Exception as exc:
            logger.exception(
                "Failed to finalize Whisper session session_id=%s error=%s",
                session_id,
                exc,
            )
            raise

    def get_current_text(self, session_id: str) -> str:
        """Get transcription accumulated so far from Whisper API."""
        try:
            client = self._get_client()
            response = client.get(f"/sessions/{session_id}/partial")
            response.raise_for_status()
            data = response.json()
            return data.get("partial_text", "")
        except Exception:
            return ""

    def get_session_consultation_id(self, session_id: str) -> int:
        """Get consultation_id for a session from Whisper API."""
        try:
            client = self._get_client()
            response = client.get(f"/sessions/{session_id}/consultation-id")
            response.raise_for_status()
            return response.json()["consultation_id"]
        except Exception as exc:
            logger.warning(
                "Failed to get consultation_id from Whisper session_id=%s error=%s",
                session_id,
                exc,
            )
            return 0
