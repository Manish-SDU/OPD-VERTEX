"""Application services for transcript normalization and report generation."""

from __future__ import annotations

from app.domain.clinical_notes.models import (
    ClinicalNoteGenerator,
    ClinicalReportRequest,
    ConsultationDocument,
    ConsultationDocumentRepository,
    GeneratedDocument,
    GeneratedDocumentRepository,
    GeneratedDocumentStatus,
    LlmExecutionMetadata,
    LlmHealthStatus,
    LocalLlmHealthService,
    PromptRepository,
    TranscriptNormalizationRequest,
    TranscriptNormalizer,
)
from app.domain.common.types import utcnow
from app.domain.consultations.models import ConsultationRepository, ConsultationStatus
from app.infrastructure.logging import apply_logging_aspect


NORMALIZATION_PROMPT_ID = "transcript_normalization_v1"
CLINICAL_REPORT_PROMPT_ID = "clinical_report_generation_v2"


@apply_logging_aspect("service", "transcript_normalization")
class TranscriptNormalizationApplicationService:
    def __init__(
        self,
        consultation_doc_repository: ConsultationDocumentRepository,
        prompt_repository: PromptRepository,
        transcript_normalizer: TranscriptNormalizer,
    ) -> None:
        self.consultation_doc_repository = consultation_doc_repository
        self.prompt_repository = prompt_repository
        self.transcript_normalizer = transcript_normalizer

    def normalize_for_consultation(
        self, consultation_id: int, *, force: bool = False
    ) -> ConsultationDocument:
        consultation_doc = self.consultation_doc_repository.get_by_consultation_id(
            consultation_id
        )
        if consultation_doc is None:
            raise ValueError(f"Consultation document {consultation_id} was not found.")

        raw_text = consultation_doc.transcript.full_text.strip()
        if not raw_text:
            raise ValueError(
                f"Consultation {consultation_id} does not have a stored transcript."
            )

        if consultation_doc.normalized_transcript and not force:
            return consultation_doc

        prompt = self.prompt_repository.get_by_id(NORMALIZATION_PROMPT_ID)
        if prompt is None:
            raise ValueError(
                f"Prompt '{NORMALIZATION_PROMPT_ID}' is missing from llm_prompts."
            )

        normalized = self.transcript_normalizer.normalize(
            TranscriptNormalizationRequest(
                consultation_id=consultation_id,
                transcript_text=raw_text,
                prompt=prompt,
            )
        )

        now = utcnow()
        consultation_doc.normalized_transcript = normalized
        consultation_doc.normalization_metadata = LlmExecutionMetadata(
            model_name=prompt.model_target or "qwen3:8b",
            prompt_id=prompt.id,
            prompt_version=prompt.version,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
            generated_at=now,
        )
        if consultation_doc.created_at is None:
            consultation_doc.created_at = now
        consultation_doc.updated_at = now
        return self.consultation_doc_repository.save(consultation_doc)


@apply_logging_aspect("service", "clinical_notes")
class ClinicalNotesApplicationService:
    def __init__(
        self,
        consultation_repository: ConsultationRepository,
        consultation_doc_repository: ConsultationDocumentRepository,
        generated_repository: GeneratedDocumentRepository,
        prompt_repository: PromptRepository,
        normalization_service: TranscriptNormalizationApplicationService,
        note_generator: ClinicalNoteGenerator,
    ) -> None:
        self.consultation_repository = consultation_repository
        self.consultation_doc_repository = consultation_doc_repository
        self.generated_repository = generated_repository
        self.prompt_repository = prompt_repository
        self.normalization_service = normalization_service
        self.note_generator = note_generator

    def generate_report(
        self, consultation_id: int, *, regenerate: bool = False
    ) -> GeneratedDocument:
        consultation = self.consultation_repository.get_by_id(consultation_id)
        if consultation is None:
            raise ValueError(f"Consultation {consultation_id} was not found.")

        existing_document = self.generated_repository.get_by_consultation_id(
            consultation_id
        )
        if existing_document and not regenerate:
            return existing_document

        self.consultation_repository.update_status(
            consultation_id, ConsultationStatus.PROCESSING
        )

        consultation_doc = self.normalization_service.normalize_for_consultation(
            consultation_id, force=regenerate
        )
        if consultation_doc.normalized_transcript is None:
            raise ValueError(
                f"Consultation {consultation_id} does not have a normalized transcript."
            )

        prompt = self.prompt_repository.get_by_id(CLINICAL_REPORT_PROMPT_ID)
        if prompt is None:
            raise ValueError(
                f"Prompt '{CLINICAL_REPORT_PROMPT_ID}' is missing from llm_prompts."
            )

        generated_notes = self.note_generator.generate(
            ClinicalReportRequest(
                consultation_id=consultation_id,
                doctor_id=consultation.doctor_id,
                patient_id=consultation.patient_id,
                transcript_text=consultation_doc.transcript.full_text,
                normalized_transcript=consultation_doc.normalized_transcript,
                prompt=prompt,
            )
        )

        now = utcnow()
        generated_document = GeneratedDocument(
            id=existing_document.id if existing_document else None,
            consultation_id=consultation_id,
            doctor_id=consultation.doctor_id,
            patient_id=consultation.patient_id,
            generated_output=generated_notes,
            normalized_transcript=consultation_doc.normalized_transcript,
            suggestive_output=None,
            report_metadata=LlmExecutionMetadata(
                model_name=prompt.model_target or "qwen3:8b",
                prompt_id=prompt.id,
                prompt_version=prompt.version,
                temperature=prompt.temperature,
                max_tokens=prompt.max_tokens,
                generated_at=now,
            ),
            suggestive_metadata=None,
            doctor_edits=[],
            status=GeneratedDocumentStatus.PENDING_REVIEW,
            approved_at=None,
            created_at=existing_document.created_at if existing_document else now,
            updated_at=now,
        )
        saved_document = self.generated_repository.save(generated_document)

        consultation_doc.ai_clinical_notes = saved_document.generated_output
        consultation_doc.ai_suggestions = None
        consultation_doc.updated_at = now
        if consultation_doc.created_at is None:
            consultation_doc.created_at = now
        self.consultation_doc_repository.save(consultation_doc)

        self.consultation_repository.update_status(
            consultation_id, ConsultationStatus.REVIEW
        )
        return saved_document


@apply_logging_aspect("service", "llm_health")
class LlmHealthApplicationService:
    def __init__(self, health_service: LocalLlmHealthService) -> None:
        self.health_service = health_service

    def check(self) -> LlmHealthStatus:
        return self.health_service.check_health()
