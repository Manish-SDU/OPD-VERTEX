"""Faster-Whisper API client - communicates with Whisper microservice."""

from __future__ import annotations

import httpx

from app.domain.transcriptions.models import (
    StreamingTranscriptChunk,
    StreamingTranscriptionService,
    TranscriptResult,
    TranscriptionService,
)

# Whisper API service URL
WHISPER_API_URL = "http://whisper:8001"


class FasterWhisperTranscriptionService(TranscriptionService):
    """Batch transcription service for complete audio files (via Whisper API)."""

    def __init__(self, model_size: str = "base", device: str = "cuda"):
        self.http_client = None

    def _get_client(self):
        """Lazy initialize HTTP client."""
        if self.http_client is None:
            self.http_client = httpx.Client(base_url=WHISPER_API_URL, timeout=60.0)
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

    def _get_client(self):
        """Lazy initialize HTTP client."""
        if self.http_client is None:
            print(f"[DEBUG] Creating httpx client to {WHISPER_API_URL}")
            self.http_client = httpx.Client(base_url=WHISPER_API_URL, timeout=60.0)
        return self.http_client

    def start_streaming(self, consultation_id: int) -> str:
        """Initialize a streaming session via Whisper API."""
        try:
            client = self._get_client()
            print(
                f"[DEBUG] Posting to /sessions/start with consultation_id={consultation_id}"
            )
            response = client.post(
                "/sessions/start",
                json={
                    "consultation_id": consultation_id,
                    "chunk_duration": self.chunk_duration,
                    "sample_rate": self.sample_rate,
                },
            )
            print(
                f"[DEBUG] Response status: {response.status_code}, body: {response.text}"
            )
            response.raise_for_status()
            data = response.json()
            return data["session_id"]
        except Exception as e:
            print(f"[ERROR] Failed to start streaming: {e}")
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
        except Exception as e:
            print(f"[ERROR] Failed to add audio chunk: {e}")
            raise

    def get_completed_results(self, session_id: str) -> list[dict]:
        """Get completed transcription results from Whisper API."""
        try:
            client = self._get_client()
            response = client.get(f"/sessions/{session_id}/partial")
            response.raise_for_status()
            data = response.json()
            return [{"text": data.get("partial_text", "")}]
        except Exception as e:
            print(f"[ERROR] Failed to get completed results: {e}")
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
        except Exception as e:
            print(f"[ERROR] Failed to finalize session: {e}")
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
        except Exception as e:
            print(f"[ERROR] Could not get consultation_id for {session_id}: {e}")
            return 0
