"""Unit tests for mock infrastructure services."""

from __future__ import annotations

from app.domain.suggestive_mode.models import RiskLevel
from app.infrastructure.persistence.in_memory.repositories import (
    InMemoryConsultationDocumentRepository,
    InMemoryGeneratedDocumentRepository,
    InMemoryPromptRepository,
    InMemoryEmailTemplateRepository,
    MockClinicalNoteGenerator,
    MockEmailService,
    MockPdfGenerator,
    MockSuggestiveModeService,
    MockTranscriptionService,
)
from app.domain.clinical_notes.models import ConsultationDocument


class TestMockTranscriptionService:
    def test_returns_transcript_result(self, transcription_service):
        result = transcription_service.transcribe(42)
        assert result.consultation_id == 42
        assert len(result.full_text) > 0

    def test_language_default(self, transcription_service):
        result = transcription_service.transcribe(1)
        assert result.language == "en"


class TestMockClinicalNoteGenerator:
    def test_generates_document(self, note_generator):
        doc = note_generator.generate(10, "Patient has headache")
        assert doc.consultation_id == 10
        assert doc.generated_output.chief_complaint == "Mock complaint"
        assert doc.generated_output.diagnosis == "Mock diagnosis"

    def test_saves_to_repository(self, generated_doc_repo, note_generator):
        note_generator.generate(77, "test transcript")
        assert generated_doc_repo.get_by_consultation_id(77) is not None


class TestMockSuggestiveModeService:
    def test_returns_green_risk(self, suggestive_service):
        review = suggestive_service.review(1, "{}")
        assert review.overall_risk_level == RiskLevel.GREEN
        assert review.consultation_id == 1


class TestMockPdfGenerator:
    def test_returns_file_path(self, pdf_generator):
        path = pdf_generator.generate_prescription_pdf(42)
        assert "42" in path
        assert path.endswith(".pdf")


class TestMockEmailService:
    def test_returns_status_message(self, email_service):
        msg = email_service.send_prescription_email(1, "user@example.com")
        assert "user@example.com" in msg


class TestConsultationDocumentRepository:
    def test_save_and_retrieve(self):
        repo = InMemoryConsultationDocumentRepository()
        doc = ConsultationDocument(
            consultation_id=5,
            transcript={"full_text": "hello world"},
        )
        repo.save(doc)
        retrieved = repo.get_by_consultation_id(5)
        assert retrieved is not None
        assert retrieved.transcript["full_text"] == "hello world"

    def test_get_nonexistent_returns_none(self):
        repo = InMemoryConsultationDocumentRepository()
        assert repo.get_by_consultation_id(999) is None


class TestPromptRepository:
    def test_list_prompts(self, prompt_repo):
        prompts = prompt_repo.list_prompts()
        assert len(prompts) >= 2

    def test_get_by_id(self, prompt_repo):
        prompt = prompt_repo.get_by_id("prescription_generation_v1")
        assert prompt is not None
        assert prompt.prompt_name == "Prescription & Clinical Notes Generator"

    def test_get_by_id_unknown(self, prompt_repo):
        assert prompt_repo.get_by_id("nonexistent") is None


class TestEmailTemplateRepository:
    def test_list_templates(self, email_template_repo):
        templates = email_template_repo.list_templates()
        assert len(templates) >= 1

    def test_get_by_id(self, email_template_repo):
        t = email_template_repo.get_by_id("prescription_delivery_v1")
        assert t is not None
        assert "Prescription" in t.template_name

    def test_get_by_id_unknown(self, email_template_repo):
        assert email_template_repo.get_by_id("nonexistent") is None
