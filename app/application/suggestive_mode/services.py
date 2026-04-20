"""Application service for second-pass suggestive review."""

from __future__ import annotations

from app.domain.clinical_notes.models import (
    ConsultationDocumentRepository,
    GeneratedDocumentRepository,
    LlmExecutionMetadata,
    PromptRepository,
)
from app.domain.common.types import utcnow
from app.domain.consultations.models import ConsultationRepository, ConsultationStatus
from app.domain.suggestive_mode.models import (
    SuggestiveModeService,
    SuggestiveReview,
    SuggestiveReviewRequest,
)
from app.application.suggestive_mode.rules import (
    build_deterministic_suggestions,
    merge_suggestive_reviews,
)
from app.infrastructure.logging import apply_logging_aspect


SUGGESTIVE_REVIEW_PROMPT_ID = "suggestive_mode_v3"


@apply_logging_aspect("service", "suggestive_mode")
class SuggestiveReviewApplicationService:
    def __init__(
        self,
        consultation_repository: ConsultationRepository,
        consultation_doc_repository: ConsultationDocumentRepository,
        generated_repository: GeneratedDocumentRepository,
        prompt_repository: PromptRepository,
        suggestive_service: SuggestiveModeService,
    ) -> None:
        self.consultation_repository = consultation_repository
        self.consultation_doc_repository = consultation_doc_repository
        self.generated_repository = generated_repository
        self.prompt_repository = prompt_repository
        self.suggestive_service = suggestive_service

    def run_review(
        self, consultation_id: int, *, regenerate: bool = False
    ) -> SuggestiveReview:
        consultation = self.consultation_repository.get_by_id(consultation_id)
        if consultation is None:
            raise ValueError(f"Consultation {consultation_id} was not found.")

        generated_document = self.generated_repository.get_by_consultation_id(
            consultation_id
        )
        if generated_document is None:
            raise ValueError(
                f"Consultation {consultation_id} does not have a generated draft yet."
            )

        if generated_document.suggestive_output and not regenerate:
            return generated_document.suggestive_output

        prompt = self.prompt_repository.get_by_id(SUGGESTIVE_REVIEW_PROMPT_ID)
        if prompt is None:
            raise ValueError(
                f"Prompt '{SUGGESTIVE_REVIEW_PROMPT_ID}' is missing from llm_prompts."
            )

        review = self.suggestive_service.review(
            SuggestiveReviewRequest(
                consultation_id=consultation_id,
                doctor_id=consultation.doctor_id,
                patient_id=consultation.patient_id,
                generated_report=generated_document.generated_output.model_dump(
                    exclude={"report_markdown"}
                ),
                normalized_transcript=generated_document.normalized_transcript.model_dump()
                if generated_document.normalized_transcript is not None
                else None,
                system_prompt=prompt.system_prompt,
                user_prompt_template=prompt.user_prompt_template,
                temperature=prompt.temperature,
                max_tokens=prompt.max_tokens,
                requested_at=utcnow(),
            )
        )

        deterministic_suggestions = build_deterministic_suggestions(
            generated_report=generated_document.generated_output.model_dump(
                exclude={"report_markdown"}
            ),
            normalized_transcript=generated_document.normalized_transcript.model_dump()
            if generated_document.normalized_transcript is not None
            else None,
        )
        review = merge_suggestive_reviews(review, deterministic_suggestions)

        now = utcnow()
        generated_document.suggestive_output = review
        generated_document.suggestive_metadata = LlmExecutionMetadata(
            model_name=prompt.model_target or "qwen3:8b",
            prompt_id=prompt.id,
            prompt_version=prompt.version,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
            generated_at=now,
        )
        generated_document.updated_at = now
        self.generated_repository.save(generated_document)

        consultation_document = self.consultation_doc_repository.get_by_consultation_id(
            consultation_id
        )
        if consultation_document is not None:
            consultation_document.ai_suggestions = review
            consultation_document.updated_at = now
            self.consultation_doc_repository.save(consultation_document)

        self.consultation_repository.update_status(
            consultation_id, ConsultationStatus.REVIEW
        )
        return review

    def get_review(self, consultation_id: int) -> SuggestiveReview:
        generated_document = self.generated_repository.get_by_consultation_id(
            consultation_id
        )
        if generated_document is None or generated_document.suggestive_output is None:
            raise ValueError(
                f"Consultation {consultation_id} does not have a suggestive review yet."
            )
        return generated_document.suggestive_output
