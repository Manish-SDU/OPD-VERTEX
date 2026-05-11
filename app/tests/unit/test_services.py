"""Unit tests for application services."""

from datetime import date

import pytest

from app.domain.audit.models import AuditLog
from app.domain.clinical_notes.models import ConsultationDocument, TranscriptDocument
from app.domain.consultations.models import (
    ConsultationCreateRequest,
    ConsultationStatus,
)
from app.domain.patients.models import PatientCreateRequest
from app.domain.prescriptions.models import Medication
from app.domain.suggestive_mode.models import RiskLevel


class TestPatientApplicationService:
    def test_list_patients(self, patient_app_service):
        patients = patient_app_service.list_patients()
        assert len(patients) >= 2

    def test_get_patient(self, patient_app_service):
        patient = patient_app_service.get_patient(1)
        assert patient is not None
        assert patient.first_name == "Giulia"

    def test_get_patient_not_found(self, patient_app_service):
        assert patient_app_service.get_patient(999) is None

    def test_create_patient(self, patient_app_service):
        req = PatientCreateRequest(
            first_name="New",
            last_name="Patient",
            date_of_birth=date(1995, 6, 15),
            email="new@example.local",
            password_hash="test123",
        )
        created = patient_app_service.create_patient(req)
        assert created.first_name == "New"
        assert created.id is not None


class TestConsultationApplicationService:
    def test_list_consultations(self, consultation_app_service):
        consultations = consultation_app_service.list_consultations()
        assert len(consultations) >= 2

    def test_get_consultation(self, consultation_app_service):
        consultation = consultation_app_service.get_consultation(1)
        assert consultation is not None
        assert consultation.doctor_id == 1

    def test_get_consultation_not_found(self, consultation_app_service):
        assert consultation_app_service.get_consultation(999) is None

    def test_create_consultation(self, consultation_app_service):
        req = ConsultationCreateRequest(patient_id=1)
        created = consultation_app_service.create_consultation(req, doctor_id=1)
        assert created.id is not None
        assert created.status == ConsultationStatus.RECORDING
        assert created.started_at is not None


class TestPrescriptionApplicationService:
    def test_list_prescriptions(self, prescription_app_service):
        prescriptions = prescription_app_service.list_prescriptions()
        assert len(prescriptions) >= 1

    def test_get_prescription(self, prescription_app_service):
        prescription = prescription_app_service.get_prescription(1)
        assert prescription is not None
        assert prescription.diagnosis == "Essential hypertension, controlled"

    def test_get_prescription_not_found(self, prescription_app_service):
        assert prescription_app_service.get_prescription(999) is None


class TestAuditApplicationService:
    def test_recent_entries(self, audit_app_service, audit_repo):
        audit_repo.append(AuditLog(user_id=1, user_role="doctor", action="LOGIN"))
        entries = audit_app_service.recent_entries()
        assert len(entries) >= 1
        assert entries[0].action == "LOGIN"


class TestReviewApplicationService:
    def test_build_review_context_reads_existing_documents(
        self, review_app_service, consultation_doc_repo
    ):
        consultation_doc_repo.save(
            ConsultationDocument(
                consultation_id=1,
                transcript=TranscriptDocument(full_text="Stored transcript."),
            )
        )
        consultation_doc, generated_doc, review = (
            review_app_service.build_review_context(1)
        )

        assert consultation_doc is not None
        assert consultation_doc.consultation_id == 1
        assert generated_doc is not None
        assert generated_doc.consultation_id == 1
        assert review.summary


class TestClinicalNotesApplicationService:
    def test_generate_report_from_seeded_structured_transcript_populates_fields(
        self, clinical_notes_app_service
    ):
        document = clinical_notes_app_service.generate_report(4102, regenerate=True)

        assert (
            document.generated_output.chief_complaint
            == "Dizziness when standing up since last night."
        )
        assert (
            document.generated_output.diagnosis
            == "Orthostatic dizziness likely related to mild dehydration."
        )
        assert document.generated_output.medications
        assert "Complete blood count" in document.generated_output.lab_tests_ordered
        assert document.generated_output.patient_instructions.startswith(
            "Increase oral fluids"
        )

    def test_generate_report_creates_generated_document(
        self,
        consultation_doc_repo,
        generated_doc_repo,
        clinical_notes_app_service,
    ):
        consultation_doc_repo.save(
            ConsultationDocument(
                consultation_id=1,
                transcript=TranscriptDocument(full_text="Patient reports headache."),
            )
        )

        document = clinical_notes_app_service.generate_report(1, regenerate=True)

        assert document.consultation_id == 1
        assert document.normalized_transcript is not None
        assert document.generated_output.diagnosis == "Mock diagnosis"
        assert generated_doc_repo.get_by_consultation_id(1) is not None
        assert (
            consultation_doc_repo.get_by_consultation_id(1).ai_clinical_notes
            is not None
        )

    def test_generate_report_raises_for_missing_consultation(
        self, clinical_notes_app_service
    ):
        with pytest.raises(ValueError, match="Consultation 999 was not found"):
            clinical_notes_app_service.generate_report(999, regenerate=True)

    def test_generate_report_handles_noisy_asr_transcript(
        self,
        consultation_doc_repo,
        generated_doc_repo,
        clinical_notes_app_service,
    ):
        consultation_doc_repo.save(
            ConsultationDocument(
                consultation_id=2,
                transcript=TranscriptDocument(
                    full_text=(
                        "docter says hello uh patient reports dizzi dizzy [noise] "
                        "after standing no chest pain no fever current med lisinopril"
                    )
                ),
            )
        )

        document = clinical_notes_app_service.generate_report(2, regenerate=True)

        assert document.normalized_transcript is not None
        assert "  " not in document.normalized_transcript.normalized_text
        assert generated_doc_repo.get_by_consultation_id(2) is not None

    def test_generate_report_handles_long_transcript(
        self,
        consultation_doc_repo,
        generated_doc_repo,
        clinical_notes_app_service,
    ):
        long_transcript = " ".join(
            "Patient reports persistent fatigue and poor sleep." for _ in range(1500)
        )
        consultation_doc_repo.save(
            ConsultationDocument(
                consultation_id=1,
                transcript=TranscriptDocument(full_text=long_transcript),
            )
        )

        document = clinical_notes_app_service.generate_report(1, regenerate=True)
        stored = generated_doc_repo.get_by_consultation_id(1)

        assert len(document.normalized_transcript.raw_text) > 10000
        assert stored is not None
        assert stored.generated_output.diagnosis == "Mock diagnosis"


class TestSuggestiveReviewApplicationService:
    def test_seeded_allergy_case_produces_suggestive_warning(
        self,
        clinical_notes_app_service,
        suggestive_review_app_service,
        generated_doc_repo,
    ):
        generated = clinical_notes_app_service.generate_report(4103, regenerate=True)
        generated.generated_output.medications = [
            Medication(
                name="Amoxicillin",
                dosage="500 mg",
                frequency="three times daily",
                duration="7 days",
                route="oral",
            )
        ]
        generated_doc_repo.save(generated)

        review = suggestive_review_app_service.run_review(4103, regenerate=True)

        assert review.overall_risk_level == RiskLevel.RED
        assert any(
            suggestion.title == "Penicillin allergy conflict"
            for suggestion in review.suggestions
        )

    def test_run_review_persists_suggestive_output(
        self,
        consultation_doc_repo,
        clinical_notes_app_service,
        suggestive_review_app_service,
        generated_doc_repo,
    ):
        consultation_doc_repo.save(
            ConsultationDocument(
                consultation_id=1,
                transcript=TranscriptDocument(full_text="Patient reports dizziness."),
            )
        )
        clinical_notes_app_service.generate_report(1, regenerate=True)

        review = suggestive_review_app_service.run_review(1, regenerate=True)
        stored = generated_doc_repo.get_by_consultation_id(1)

        assert review.overall_risk_level == RiskLevel.GREEN
        assert stored is not None
        assert stored.suggestive_output is not None

    def test_approve_review_projects_into_sql_shape(
        self,
        consultation_doc_repo,
        clinical_notes_app_service,
        review_app_service,
        prescription_repo,
    ):
        consultation_doc_repo.save(
            ConsultationDocument(
                consultation_id=1,
                transcript=TranscriptDocument(full_text="Patient reports dizziness."),
            )
        )
        clinical_notes_app_service.generate_report(1, regenerate=True)

        prescription = review_app_service.approve_review(1)

        assert prescription.is_approved is True
        assert prescription_repo.get_by_id(prescription.id) is not None

    def test_end_to_end_review_flow_persists_drafts_and_projects_sql(
        self,
        consultation_repo,
        consultation_doc_repo,
        generated_doc_repo,
        clinical_notes_app_service,
        suggestive_review_app_service,
        review_app_service,
        prescription_repo,
    ):
        consultation_doc_repo.save(
            ConsultationDocument(
                consultation_id=2,
                transcript=TranscriptDocument(
                    full_text=(
                        "Doctor: You have sinus pressure and congestion. "
                        "Patient: Penicillin caused a rash before. "
                        "Doctor: I will document the allergy and review treatment options."
                    )
                ),
            )
        )

        generated = clinical_notes_app_service.generate_report(2, regenerate=True)
        assert str(generated.status) == "pending_review"
        suggestive = suggestive_review_app_service.run_review(2, regenerate=True)
        prescription = review_app_service.approve_review(2)
        stored_doc = consultation_doc_repo.get_by_consultation_id(2)
        stored_generated = generated_doc_repo.get_by_consultation_id(2)

        assert suggestive.overall_risk_level == RiskLevel.GREEN
        assert stored_doc is not None
        assert stored_doc.ai_clinical_notes is not None
        assert stored_doc.ai_suggestions is not None
        assert stored_generated is not None
        assert stored_generated.suggestive_output is not None
        assert stored_generated.status == "approved"
        assert consultation_repo.get_by_id(2).status == ConsultationStatus.APPROVED
        assert prescription_repo.get_by_id(prescription.id) is not None
