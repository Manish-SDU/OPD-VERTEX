"""Transcription application service orchestration."""

from __future__ import annotations

from datetime import datetime
from app.domain.clinical_notes.models import (
    ConsultationDocument,
    ConsultationDocumentRepository,
    TranscriptDocument,
)
from app.domain.consultations.models import ConsultationRepository, ConsultationStatus
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
        consultation_doc_repository: ConsultationDocumentRepository | None = None,
        consultation_repository: ConsultationRepository | None = None,
    ):
        self.streaming_service = streaming_service
        self.temp_chunk_repo = temp_chunk_repo
        self.consultation_doc_repository = consultation_doc_repository
        self.consultation_repository = consultation_repository

    def start_transcription_session(self, consultation_id: int) -> str:
        """Start a new transcription session for a consultation."""
        if self.consultation_repository is not None:
            self.consultation_repository.update_status(
                consultation_id, ConsultationStatus.TRANSCRIBING
            )
        return self.streaming_service.start_streaming(consultation_id)

    def process_audio_chunk(
        self, session_id: str, audio_bytes: bytes
    ) -> StreamingTranscriptChunk | None:
        """Process incoming audio chunk AND save to temporary storage."""
        chunk = self.streaming_service.add_audio_chunk(session_id, audio_bytes)

        if chunk:
            # Get actual consultation_id from streaming service
            consultation_id = self.streaming_service.get_session_consultation_id(
                session_id
            )

            # Get the actual transcribed text (not the placeholder [processing...])
            partial_text = self.streaming_service.get_current_text(session_id)

            # Only save if we have actual text
            if (
                partial_text
                and partial_text.strip()
                and partial_text != "[processing...]"
            ):
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

    def save_final_transcript(
        self, consultation_id: int, session_id: str
    ) -> TranscriptResult:
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

    def finalize_and_persist_transcription(self, session_id: str) -> TranscriptResult:
        """Finalize a live session and persist the transcript into Mongo-backed docs."""
        result = self.complete_transcription(session_id)
        self._persist_transcript(result.consultation_id, result)
        return result

    def persist_saved_transcription(
        self, consultation_id: int, session_id: str
    ) -> TranscriptResult:
        """Persist the transcript assembled from temporary chunks."""
        result = self.save_final_transcript(consultation_id, session_id)
        if not result.full_text.strip():
            raise ValueError(
                f"Consultation {consultation_id} cannot be saved without a transcript."
            )
        self._persist_transcript(consultation_id, result)
        return result

    def inject_demo_text(self, session_id: str, text: str) -> None:
        """Inject text for demo / no-mic mode. Saves as a single temp chunk."""
        if hasattr(self.streaming_service, "inject_text"):
            self.streaming_service.inject_text(session_id, text)
        consultation_id = self.streaming_service.get_session_consultation_id(session_id)
        chunk = TemporaryTranscriptChunk(
            consultation_id=consultation_id,
            session_id=session_id,
            chunk_id=1,
            text=text,
            timestamp=0.0,
            is_final=True,
            created_at=datetime.utcnow(),
        )
        self.temp_chunk_repo.save_chunk(chunk)

    def _persist_transcript(
        self, consultation_id: int, result: TranscriptResult
    ) -> TranscriptResult:
        if self.consultation_doc_repository is None:
            raise ValueError("Consultation document repository is not configured.")

        consultation_doc = self.consultation_doc_repository.get_by_consultation_id(
            consultation_id
        )
        if consultation_doc is None:
            consultation_doc = ConsultationDocument(
                consultation_id=consultation_id,
                transcript=TranscriptDocument(full_text=result.full_text),
            )
        else:
            consultation_doc.transcript.full_text = result.full_text
        consultation_doc.updated_at = datetime.utcnow()
        if consultation_doc.created_at is None:
            consultation_doc.created_at = consultation_doc.updated_at
        self.consultation_doc_repository.save(consultation_doc)

        if self.consultation_repository is not None:
            self.consultation_repository.update_status(
                consultation_id, ConsultationStatus.PROCESSING
            )
        return result
