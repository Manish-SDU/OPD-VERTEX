"""Transcription domain models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

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
    def get_completed_results(self, session_id: str) -> list[dict]:
        """Return list of completed transcription chunks so far."""

    @abstractmethod
    def finalize_session(self, session_id: str) -> TranscriptResult:
        """End streaming and return combined transcript."""


class TemporaryTranscriptChunk(BaseModel):
    """Temporary storage for streaming transcript chunks during recording."""

    id: str | None = None
    consultation_id: int
    session_id: str
    chunk_id: int
    text: str
    timestamp: float
    is_final: bool = False
    created_at: datetime | None = None


class TemporaryTranscriptChunkRepository(ABC):
    @abstractmethod
    def save_chunk(self, chunk: TemporaryTranscriptChunk) -> TemporaryTranscriptChunk:
        """Save a partial transcript chunk temporarily."""

    @abstractmethod
    def get_chunks_by_consultation(
        self, consultation_id: int
    ) -> list[TemporaryTranscriptChunk]:
        """Retrieve all chunks for a consultation."""

    @abstractmethod
    def delete_chunks_by_consultation(self, consultation_id: int) -> None:
        """Clear chunks after they're saved to main database."""

    @abstractmethod
    def delete_chunks_by_session(self, session_id: str) -> None:
        """Delete all chunks for a specific session."""
