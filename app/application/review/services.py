"""Review workflow application service."""

from __future__ import annotations

from app.domain.clinical_notes.models import (
    ClinicalNoteGenerator,
    ConsultationDocument,
    ConsultationDocumentRepository,
    GeneratedDocument,
    GeneratedDocumentRepository,
    TranscriptDocument,
)
from app.domain.suggestive_mode.models import SuggestiveModeService, SuggestiveReview
from app.domain.transcription.models import TranscriptionService
from app.infrastructure.logging import apply_logging_aspect


@apply_logging_aspect("service", "review")
class ReviewApplicationService:
    def __init__(
        self,
        consultation_doc_repository: ConsultationDocumentRepository,
        generated_repository: GeneratedDocumentRepository,
        transcription_service: TranscriptionService,
        note_generator: ClinicalNoteGenerator,
        suggestive_service: SuggestiveModeService,
    ) -> None:
        self.consultation_doc_repository = consultation_doc_repository
        self.generated_repository = generated_repository
        self.transcription_service = transcription_service
        self.note_generator = note_generator
        self.suggestive_service = suggestive_service

    def build_review_context(
        self, consultation_id: int
    ) -> tuple[ConsultationDocument | None, GeneratedDocument | None, SuggestiveReview]:
        # Get or create transcript
        con_doc = self.consultation_doc_repository.get_by_consultation_id(
            consultation_id
        )
        if con_doc is None:
            transcript_result = self.transcription_service.transcribe(consultation_id)
            con_doc = ConsultationDocument(
                consultation_id=consultation_id,
                transcript=TranscriptDocument(
                    full_text=transcript_result.full_text,
                    file_name=transcript_result.file_path or None,
                ),
            )
            con_doc = self.consultation_doc_repository.save(con_doc)

        # Get or create generated notes
        gen_doc = self.generated_repository.get_by_consultation_id(consultation_id)
        if gen_doc is None:
            transcript_text = con_doc.transcript.full_text
            gen_doc = self.note_generator.generate(consultation_id, transcript_text)

        # Run suggestive review
        review = self.suggestive_service.review(
            consultation_id, gen_doc.generated_output.model_dump_json()
        )
        return con_doc, gen_doc, review
