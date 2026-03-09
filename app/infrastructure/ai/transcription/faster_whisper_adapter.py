"""Placeholder Faster-Whisper adapter."""

from __future__ import annotations

from app.domain.transcription.models import TranscriptDocument, TranscriptionService


class FasterWhisperTranscriptionService(TranscriptionService):
    def transcribe(self, consultation_id: str) -> TranscriptDocument:
        # TODO: integrate local audio capture storage and Faster-Whisper inference.
        return TranscriptDocument(
            id=f"trn_{consultation_id}",
            consultation_id=consultation_id,
            raw_text="TODO: replace placeholder transcription adapter.",
        )
