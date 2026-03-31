"""Transcription domain models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pydantic import BaseModel


class TranscriptResult(BaseModel):
    """Output from Faster-Whisper. Stored inside consultation_documents."""

    consultation_id: int
    file_path: str = ""
    full_text: str = ""
    language: str = "en"


class StreamingTranscriptChunk(BaseModel):
    """Single chunk result from streaming transcription."""

    chunk_id: int
    text: str
    timestamp: float  # seconds in audio
    is_final: bool = False


class TranscriptionService(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> TranscriptResult:
        """Run speech-to-text on recorded audio file."""


class StreamingTranscriptionService(ABC):
    @abstractmethod
    def start_streaming(self, consultation_id: int) -> str:
        """Initialize streaming session. Returns session_id."""

    @abstractmethod
    def add_audio_chunk(
        self, session_id: str, audio_bytes: bytes
    ) -> StreamingTranscriptChunk | None:
        """Process audio chunk. Returns transcription if ready."""

    @abstractmethod
    def finalize_session(self, session_id: str) -> TranscriptResult:
        """End streaming and return combined transcript."""
