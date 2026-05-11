"""Unit tests for mock infrastructure services."""

from __future__ import annotations

from app.domain.clinical_notes.models import (
    ClinicalReportRequest,
    ConsultationDocument,
    GeneratedClinicalNotes,
    LlmPromptConfig,
    NormalizedTranscript,
    PrescriptionArtifact,
    TranscriptNormalizationRequest,
)
from app.domain.prescriptions.models import Prescription
from app.domain.suggestive_mode.models import RiskLevel, SuggestiveReviewRequest
from app.infrastructure.persistence.in_memory.repositories import (
    InMemoryConsultationDocumentRepository,
    InMemoryPrescriptionArtifactRepository,
    MockEmailService,
)


class TestMockTranscriptionService:
    def test_returns_transcript_result(self, transcription_service):
        result = transcription_service.transcribe(42)
        assert result.consultation_id == 42
        assert len(result.full_text) > 0

    def test_language_default(self, transcription_service):
        result = transcription_service.transcribe(1)
        assert result.language == "en"


class TestMockClinicalNoteGenerator:
    def test_generates_structured_notes(self, note_generator):
        notes = note_generator.generate(
            ClinicalReportRequest(
                consultation_id=10,
                doctor_id=1,
                patient_id=1,
                transcript_text="Patient has headache",
                normalized_transcript=NormalizedTranscript(
                    raw_text="Patient has headache",
                    normalized_text="Patient has headache",
                ),
                prompt=LlmPromptConfig(
                    id="clinical_report_generation_v3",
                    prompt_name="Clinical Report Generation (Template Output)",
                ),
            )
        )
        assert notes.chief_complaint == "Mock complaint"
        assert notes.diagnosis == "Mock diagnosis"


class TestMockSuggestiveModeService:
    def test_returns_green_risk(self, suggestive_service):
        review = suggestive_service.review(
            SuggestiveReviewRequest(
                consultation_id=1,
                doctor_id=1,
                patient_id=1,
                generated_report=GeneratedClinicalNotes(
                    diagnosis="Mock diagnosis"
                ).model_dump(),
                system_prompt="system",
                user_prompt_template="template",
            )
        )
        assert review.overall_risk_level == RiskLevel.GREEN
        assert review.consultation_id == 1

    def test_flags_allergy_conflict_when_medication_is_contraindicated(
        self, suggestive_service
    ):
        review = suggestive_service.review(
            SuggestiveReviewRequest(
                consultation_id=4103,
                doctor_id=1,
                patient_id=5103,
                generated_report=GeneratedClinicalNotes(
                    diagnosis="Acute bacterial rhinosinusitis",
                    allergies="Penicillin allergy causing rash",
                    medications=[
                        {
                            "name": "Amoxicillin",
                            "dosage": "500 mg",
                            "frequency": "three times daily",
                            "duration": "7 days",
                            "route": "oral",
                        }
                    ],
                ).model_dump(),
                normalized_transcript={
                    "normalized_text": "Penicillin allergy causing rash"
                },
                system_prompt="system",
                user_prompt_template="template",
            )
        )
        assert review.overall_risk_level == RiskLevel.RED
        assert review.suggestions
        assert review.suggestions[0].title == "Penicillin allergy conflict"


class TestMockTranscriptNormalizer:
    def test_returns_normalized_transcript(self, transcript_normalizer):
        normalized = transcript_normalizer.normalize(
            TranscriptNormalizationRequest(
                consultation_id=1,
                transcript_text="Patient   reports   cough",
                prompt=LlmPromptConfig(
                    id="transcript_normalization_v1",
                    prompt_name="Transcript Normalization",
                ),
            )
        )
        # normalized_text is derived from cleaned_transcript speaker turns
        assert normalized.normalized_text != ""
        assert "  " not in normalized.normalized_text
        # Should have at least one speaker turn
        assert len(normalized.cleaned_transcript) >= 1
        assert normalized.cleaned_transcript[0].speaker in (
            "DOCTOR",
            "PATIENT",
            "UNKNOWN",
        )


class TestMockPdfGenerator:
    def test_returns_artifact_metadata(self, pdf_generator):
        artifact = pdf_generator.generate_prescription_pdf(
            Prescription(
                id=42,
                consultation_id=7,
                doctor_id=3,
                patient_id=9,
                diagnosis="Test diagnosis",
            )
        )
        assert isinstance(artifact, PrescriptionArtifact)
        assert artifact.prescription_id == 42
        assert artifact.consultation_id == 7
        assert artifact.doctor_id == 3
        assert artifact.patient_id == 9
        assert artifact.file_name.endswith(".pdf")


def test_mock_email_service():
    email_service = MockEmailService()
    msg = email_service.send_prescription_email(1, "user@example.com")
    assert "user@example.com" in msg


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
        assert retrieved.transcript.full_text == "hello world"

    def test_preloads_demo_transcripts_for_report_generation(self):
        repo = InMemoryConsultationDocumentRepository()
        retrieved = repo.get_by_consultation_id(4101)
        assert retrieved is not None
        assert "sore throat" in retrieved.transcript.full_text


class TestPrescriptionArtifactRepository:
    def test_save_and_get_latest(self, prescription_artifact_repo):
        prescription_artifact_repo.save(
            PrescriptionArtifact(
                prescription_id=7,
                consultation_id=7,
                doctor_id=1,
                patient_id=1,
                version=1,
                storage_backend="gridfs",
                gridfs_file_id="abc123",
                file_name="prescription_7_v1.pdf",
            )
        )
        latest = prescription_artifact_repo.get_latest_by_prescription_id(7)
        assert latest is not None
        assert latest.file_name == "prescription_7_v1.pdf"

    def test_get_nonexistent_returns_none(self):
        repo = InMemoryPrescriptionArtifactRepository()
        assert repo.get_latest_by_prescription_id(999) is None


class TestPromptRepository:
    def test_list_prompts(self, prompt_repo):
        prompts = prompt_repo.list_prompts()
        assert len(prompts) >= 3

    def test_get_by_id(self, prompt_repo):
        prompt = prompt_repo.get_by_id("clinical_report_generation_v3")
        assert prompt is not None
        assert prompt.prompt_name == "Clinical Report Generation (Template Output)"

    def test_get_by_id_unknown(self, prompt_repo):
        assert prompt_repo.get_by_id("nonexistent") is None


class TestEmailTemplateRepository:
    def test_list_templates(self, email_template_repo):
        templates = email_template_repo.list_templates()
        assert len(templates) >= 1

    def test_get_by_id(self, email_template_repo):
        template = email_template_repo.get_by_id("prescription_delivery_v1")
        assert template is not None
        assert "Prescription" in template.template_name

    def test_get_by_id_unknown(self, email_template_repo):
        assert email_template_repo.get_by_id("nonexistent") is None
