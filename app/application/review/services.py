"""Review workflow application service."""

from __future__ import annotations

from app.domain.clinical_notes.models import ClinicalNoteGenerator, GeneratedDocument, GeneratedDocumentRepository
from app.domain.suggestive_mode.models import SuggestiveModeService, SuggestiveReview
from app.domain.transcription.models import TranscriptDocument, TranscriptDocumentRepository, TranscriptionService


class ReviewApplicationService:
    def __init__(
        self,
        transcript_repository: TranscriptDocumentRepository,
        generated_repository: GeneratedDocumentRepository,
        transcription_service: TranscriptionService,
        note_generator: ClinicalNoteGenerator,
        suggestive_service: SuggestiveModeService,
    ) -> None:
        self.transcript_repository = transcript_repository
        self.generated_repository = generated_repository
        self.transcription_service = transcription_service
        self.note_generator = note_generator
        self.suggestive_service = suggestive_service

    def build_review_context(self, consultation_id: str) -> tuple[TranscriptDocument, GeneratedDocument, SuggestiveReview]:
        transcript = self.transcript_repository.get_by_consultation_id(consultation_id)
        if transcript is None:
            transcript = self.transcription_service.transcribe(consultation_id)

        document = self.generated_repository.get_by_consultation_id(consultation_id)
        if document is None:
            document = self.note_generator.generate(consultation_id, transcript.raw_text)

        review = self.suggestive_service.review(consultation_id, document.notes.model_dump_json())
        return transcript, document, review
