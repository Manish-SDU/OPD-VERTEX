"""Unit tests for application services.

Each test uses in-memory repositories (injected via conftest fixtures)
so no database connection is needed.
"""

from datetime import date

from app.domain.consultations.models import (
    ConsultationCreateRequest,
    ConsultationStatus,
)
from app.domain.patients.models import PatientCreateRequest
from app.domain.suggestive_mode.models import RiskLevel


# ── Patient Application Service ───────────────────────────────────────


class TestPatientApplicationService:
    def test_list_patients(self, patient_app_service):
        patients = patient_app_service.list_patients()
        assert len(patients) >= 2

    def test_get_patient(self, patient_app_service):
        p = patient_app_service.get_patient(1)
        assert p is not None
        assert p.first_name == "Giulia"

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


# ── Consultation Application Service ──────────────────────────────────


class TestConsultationApplicationService:
    def test_list_consultations(self, consultation_app_service):
        consultations = consultation_app_service.list_consultations()
        assert len(consultations) >= 2

    def test_get_consultation(self, consultation_app_service):
        c = consultation_app_service.get_consultation(1)
        assert c is not None
        assert c.doctor_id == 1

    def test_get_consultation_not_found(self, consultation_app_service):
        assert consultation_app_service.get_consultation(999) is None

    def test_create_consultation(self, consultation_app_service):
        req = ConsultationCreateRequest(patient_id=1)
        created = consultation_app_service.create_consultation(req, doctor_id=1)
        assert created.id is not None
        assert created.status == ConsultationStatus.RECORDING
        assert created.started_at is not None


# ── Prescription Application Service ──────────────────────────────────


class TestPrescriptionApplicationService:
    def test_list_prescriptions(self, prescription_app_service):
        prescriptions = prescription_app_service.list_prescriptions()
        assert len(prescriptions) >= 1

    def test_get_prescription(self, prescription_app_service):
        p = prescription_app_service.get_prescription(1)
        assert p is not None
        assert p.diagnosis == "Essential hypertension, controlled"

    def test_get_prescription_not_found(self, prescription_app_service):
        assert prescription_app_service.get_prescription(999) is None


# ── Audit Application Service ─────────────────────────────────────────


class TestAuditApplicationService:
    def test_recent_entries(self, audit_app_service):
        entries = audit_app_service.recent_entries()
        assert len(entries) >= 1
        assert entries[0].action == "LOGIN"


# ── Review Application Service ────────────────────────────────────────


class TestReviewApplicationService:
    def test_build_review_context_creates_transcript_and_notes(
        self, review_app_service
    ):
        con_doc, gen_doc, review = review_app_service.build_review_context(99)

        assert con_doc is not None
        assert con_doc.consultation_id == 99
        assert "full_text" in con_doc.transcript

        assert gen_doc is not None
        assert gen_doc.consultation_id == 99

        assert review is not None
        assert review.overall_risk_level == RiskLevel.GREEN

    def test_build_review_context_reuses_existing_docs(self, review_app_service):
        # First call creates them
        review_app_service.build_review_context(50)
        # Second call should reuse
        con_doc, gen_doc, review = review_app_service.build_review_context(50)
        assert con_doc.consultation_id == 50
        assert gen_doc.consultation_id == 50
