"""Transcription application service orchestration."""

from __future__ import annotations

from app.domain.transcriptions.models import (
    StreamingTranscriptionService,
    StreamingTranscriptChunk,
    TranscriptResult,
)
from app.infrastructure.logging import apply_logging_aspect


@apply_logging_aspect("service", "transcriptions")
class TranscriptionApplicationService:
    """Orchestrate audio transcriptions workflow."""

    def __init__(self, streaming_service: StreamingTranscriptionService):
        self.streaming_service = streaming_service

    def start_transcription_session(self, consultation_id: int) -> str:
        """Start a new transcription session for a consultation."""
        return self.streaming_service.start_streaming(consultation_id)

    def process_audio_chunk(
        self, session_id: str, audio_bytes: bytes
    ) -> StreamingTranscriptChunk | None:
        """Process incoming audio chunk."""
        return self.streaming_service.add_audio_chunk(session_id, audio_bytes)

    def complete_transcription(self, session_id: str) -> TranscriptResult:
        """Finalize and return complete transcript."""
        return self.streaming_service.finalize_session(session_id)

    def get_partial_transcription(self, session_id: str) -> str:
        """Get what's been transcribed so far."""
        return self.streaming_service.get_current_text(session_id)