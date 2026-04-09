"""Transcription application service orchestration."""

from __future__ import annotations

from datetime import datetime
from app.domain.transcriptions.models import (
    StreamingTranscriptionService,
    StreamingTranscriptChunk,
    TranscriptResult,
    TemporaryTranscriptChunk,
    TemporaryTranscriptChunkRepository,
)
from app.infrastructure.logging import apply_logging_aspect


@apply_logging_aspect("service", "transcriptions")
class TranscriptionApplicationService:
    """Orchestrate audio transcriptions workflow."""

    def __init__(
        self, 
        streaming_service: StreamingTranscriptionService,
        temp_chunk_repo: TemporaryTranscriptChunkRepository,
    ):
        self.streaming_service = streaming_service
        self.temp_chunk_repo = temp_chunk_repo

    def start_transcription_session(self, consultation_id: int) -> str:
        """Start a new transcription session for a consultation."""
        return self.streaming_service.start_streaming(consultation_id)

    def process_audio_chunk(
        self, session_id: str, audio_bytes: bytes
    ) -> StreamingTranscriptChunk | None:
        """Process incoming audio chunk AND save to temporary storage."""
        chunk = self.streaming_service.add_audio_chunk(session_id, audio_bytes)
        
        if chunk:
            # Get actual consultation_id from streaming service
            consultation_id = self.streaming_service.get_session_consultation_id(session_id)
            
            # Get the actual transcribed text (not the placeholder [processing...])
            partial_text = self.streaming_service.get_current_text(session_id)
            
            # Only save if we have actual text
            if partial_text and partial_text.strip() and partial_text != "[processing...]":
                temp_chunk = TemporaryTranscriptChunk(
                    consultation_id=consultation_id,
                    session_id=session_id,  # ADD THIS LINE
                    chunk_id=chunk.chunk_id,
                    text=partial_text,
                    timestamp=chunk.timestamp,
                    is_final=chunk.is_final,
                    created_at=datetime.utcnow(),
                )
                self.temp_chunk_repo.save_chunk(temp_chunk)
        
        return chunk

    def complete_transcription(self, session_id: str) -> TranscriptResult:
        """Finalize and return complete transcript."""
        return self.streaming_service.finalize_session(session_id)

    def get_partial_transcription(self, session_id: str) -> str:
        """Get what's been transcribed so far."""
        return self.streaming_service.get_current_text(session_id)

    def get_completed_results(self, session_id: str) -> list[dict]:
        """Get completed transcription chunks from background processing."""
        return self.streaming_service.get_completed_results(session_id)
    
    def save_final_transcript(self, consultation_id: int, session_id: str) -> TranscriptResult:
        """Fetch chunks from a specific session and create final transcript."""
        # Get all chunks for this consultation
        temp_chunks = self.temp_chunk_repo.get_chunks_by_consultation(consultation_id)
        
        # Filter to only chunks from this session
        session_chunks = [c for c in temp_chunks if c.session_id == session_id]
        
        # Each chunk already contains cumulative text, so just take the LAST chunk's text
        full_text = ""
        if session_chunks:
            # Sort by chunk_id and take the final chunk (which has all accumulated text)
            last_chunk = sorted(session_chunks, key=lambda c: c.chunk_id)[-1]
            full_text = last_chunk.text
        
        # Create final TranscriptResult
        result = TranscriptResult(
            consultation_id=consultation_id,
            full_text=full_text,
            language="en",
        )
        
        # Clean up temporary storage for this session
        self.temp_chunk_repo.delete_chunks_by_session(session_id)
        
        return result
