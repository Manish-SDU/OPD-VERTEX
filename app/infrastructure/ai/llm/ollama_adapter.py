"""Placeholder local LLM adapters."""

from __future__ import annotations

from app.domain.clinical_notes.models import ClinicalNoteGenerator, GeneratedClinicalNotes, GeneratedDocument
from app.domain.suggestive_mode.models import SuggestiveModeService, SuggestiveReview


class OllamaClinicalNoteGenerator(ClinicalNoteGenerator):
    def generate(self, consultation_id: str, transcript_text: str) -> GeneratedDocument:
        # TODO: invoke a local LLM provider and map structured output safely.
        return GeneratedDocument(
            id=f"gen_{consultation_id}",
            consultation_id=consultation_id,
            notes=GeneratedClinicalNotes(
                subjective="TODO",
                objective="TODO",
                assessment="TODO",
                plan="TODO",
            ),
        )


class OllamaSuggestiveModeService(SuggestiveModeService):
    def review(self, consultation_id: str, document_text: str) -> SuggestiveReview:
        # TODO: run a separate local safety review prompt.
        return SuggestiveReview(consultation_id=consultation_id, suggestions=[])
