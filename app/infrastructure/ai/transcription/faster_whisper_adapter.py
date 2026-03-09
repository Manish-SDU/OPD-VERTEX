"""Placeholder Faster-Whisper adapter."""

from __future__ import annotations

from app.domain.transcription.models import TranscriptResult, TranscriptionService


class FasterWhisperTranscriptionService(TranscriptionService):
    def transcribe(self, consultation_id: int) -> TranscriptResult:
        # TODO: integrate local audio capture storage and Faster-Whisper inference.
        return TranscriptResult(
            consultation_id=consultation_id,
            full_text="TODO: replace placeholder transcription adapter.",
        )
