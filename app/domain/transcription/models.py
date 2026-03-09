"""Transcription domain models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class TranscriptDocument(BaseModel):
    id: str
    consultation_id: str
    raw_text: str
    language: str = "en"


class TranscriptDocumentRepository(ABC):
    @abstractmethod
    def get_by_consultation_id(self, consultation_id: str) -> TranscriptDocument | None:
        """Return transcript document."""

    @abstractmethod
    def save(self, transcript: TranscriptDocument) -> TranscriptDocument:
        """Persist transcript document."""


class TranscriptionService(ABC):
    @abstractmethod
    def transcribe(self, consultation_id: str) -> TranscriptDocument:
        """Run placeholder transcription."""
