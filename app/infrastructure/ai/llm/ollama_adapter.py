"""Placeholder local LLM adapters."""

from __future__ import annotations

from app.domain.clinical_notes.models import (
    ClinicalNoteGenerator,
    GeneratedClinicalNotes,
    GeneratedDocument,
)
from app.domain.suggestive_mode.models import (
    RiskLevel,
    SuggestiveModeService,
    SuggestiveReview,
)


class OllamaClinicalNoteGenerator(ClinicalNoteGenerator):
    def generate(self, consultation_id: int, transcript_text: str) -> GeneratedDocument:
        # TODO: invoke a local LLM provider and map structured output safely.
        return GeneratedDocument(
            consultation_id=consultation_id,
            doctor_id=0,
            patient_id=0,
            generated_output=GeneratedClinicalNotes(
                chief_complaint="TODO",
                diagnosis="TODO",
            ),
        )


class OllamaSuggestiveModeService(SuggestiveModeService):
    def review(self, consultation_id: int, document_json: str) -> SuggestiveReview:
        # TODO: run a separate local safety review prompt.
        return SuggestiveReview(
            consultation_id=consultation_id,
            overall_risk_level=RiskLevel.GREEN,
            summary="",
        )
