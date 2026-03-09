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


class TranscriptionService(ABC):
    @abstractmethod
    def transcribe(self, consultation_id: int) -> TranscriptResult:
        """Run speech-to-text on recorded audio."""
