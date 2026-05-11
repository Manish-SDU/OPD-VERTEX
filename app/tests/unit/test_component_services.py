"""Component tests – isolated service layer behaviour with mock infrastructure.

These sit between unit tests (which test individual classes) and integration
tests (which exercise HTTP routes through TestClient).  Each test wires a real
application-service object but uses in-memory repositories.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.application.consultations.services import ConsultationApplicationService
from app.application.patients.services import PatientApplicationService
from app.application.review.services import ReviewApplicationService
from app.domain.clinical_notes.models import (
    ConsultationDocument,
    GeneratedClinicalNotes,
    GeneratedDocument,
    GeneratedDocumentStatus,
    LlmExecutionMetadata,
    NormalizedTranscript,
    TranscriptDocument,
)
from app.domain.consultations.models import (
    Consultation,
    ConsultationCreateRequest,
    ConsultationStatus,
)
from app.domain.patients.models import Patient
from app.infrastructure.persistence.in_memory.repositories import (
    InMemoryConsultationDocumentRepository,
    InMemoryConsultationRepository,
    InMemoryGeneratedDocumentRepository,
    InMemoryPatientRepository,
    InMemoryPrescriptionRepository,
    MockEmailService,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_patient(pid: int = 1, first: str = "Alice", last: str = "Smith") -> Patient:
    return Patient(
        id=pid,
        first_name=first,
        last_name=last,
        date_of_birth=date(1985, 3, 14),
        email=f"patient{pid}@test.com",
    )


def _make_consultation(cid: int = 1, pid: int = 1, did: int = 2) -> Consultation:
    return Consultation(
        id=cid,
        patient_id=pid,
        doctor_id=did,
        status=ConsultationStatus.REVIEW,
        chief_complaint="Headache",
        started_at=datetime(2026, 1, 10, 9, 0),
    )


def _make_consultation_doc(
    cid: int = 1, text: str = "Doctor: Hello. Patient: Hi."
) -> ConsultationDocument:
    return ConsultationDocument(
        consultation_id=cid,
        transcript=TranscriptDocument(full_text=text),
        normalized_transcript=NormalizedTranscript(
            raw_text=text,
            cleaned_transcript=[
                {"speaker": "DOCTOR", "utterance": "Hello."},
                {"speaker": "PATIENT", "utterance": "Hi."},
            ],
        ),
    )


def _make_generated_doc(cid: int = 1) -> GeneratedDocument:
    return GeneratedDocument(
        consultation_id=cid,
        doctor_id=2,
        patient_id=1,
        status=GeneratedDocumentStatus.PENDING_REVIEW,
        generated_output=GeneratedClinicalNotes(
            chief_complaint="Headache",
            diagnosis="Tension headache",
            report_markdown="# Report\nPatient has tension headache.",
        ),
        llm_metadata=LlmExecutionMetadata(),
    )


# ── ConsultationApplicationService tests ─────────────────────────────────────


class TestConsultationApplicationServiceComponent:
    def test_create_consultation_with_chief_complaint(self):
        repo = InMemoryConsultationRepository()
        svc = ConsultationApplicationService(repo)
        req = ConsultationCreateRequest(patient_id=1, chief_complaint="Cough")
        c = svc.create_consultation(req, doctor_id=2)
        assert c.id is not None
        assert c.chief_complaint == "Cough"
        assert c.patient_id == 1
        assert c.doctor_id == 2
        assert c.status == ConsultationStatus.RECORDING

    def test_create_consultation_without_complaint(self):
        repo = InMemoryConsultationRepository()
        svc = ConsultationApplicationService(repo)
        c = svc.create_consultation(
            ConsultationCreateRequest(patient_id=5), doctor_id=3
        )
        assert c.chief_complaint is None

    def test_list_consultations_returns_all(self):
        repo = InMemoryConsultationRepository()
        svc = ConsultationApplicationService(repo)
        svc.create_consultation(ConsultationCreateRequest(patient_id=1), doctor_id=1)
        svc.create_consultation(ConsultationCreateRequest(patient_id=2), doctor_id=1)
        assert len(svc.list_consultations()) >= 2

    def test_get_consultation_by_id(self):
        repo = InMemoryConsultationRepository()
        svc = ConsultationApplicationService(repo)
        created = svc.create_consultation(
            ConsultationCreateRequest(patient_id=1), doctor_id=1
        )
        fetched = svc.get_consultation(created.id)
        assert fetched.id == created.id

    def test_get_nonexistent_consultation_returns_none(self):
        repo = InMemoryConsultationRepository()
        svc = ConsultationApplicationService(repo)
        assert svc.get_consultation(999) is None

    def test_consultation_status_is_recording_initially(self):
        repo = InMemoryConsultationRepository()
        svc = ConsultationApplicationService(repo)
        c = svc.create_consultation(
            ConsultationCreateRequest(patient_id=1), doctor_id=1
        )
        assert c.status == ConsultationStatus.RECORDING


# ── PatientApplicationService tests ──────────────────────────────────────────


class TestPatientApplicationServiceComponent:
    def test_list_patients_returns_seeded_data(self):
        repo = InMemoryPatientRepository()
        svc = PatientApplicationService(repo)
        patients = svc.list_patients()
        assert len(patients) > 0

    def test_get_patient_by_id(self):
        repo = InMemoryPatientRepository()
        svc = PatientApplicationService(repo)
        patients = svc.list_patients()
        first = patients[0]
        fetched = svc.get_patient(first.id)
        assert fetched.id == first.id
        assert fetched.first_name == first.first_name

    def test_search_patients_by_name(self):
        repo = InMemoryPatientRepository()
        svc = PatientApplicationService(repo)
        patients = svc.list_patients()
        if patients:
            name_fragment = patients[0].first_name[:3]
            results = svc.search_patients(name_fragment)
            assert len(results) >= 1

    def test_search_patients_empty_query_returns_all(self):
        repo = InMemoryPatientRepository()
        svc = PatientApplicationService(repo)
        all_patients = svc.list_patients()
        results = svc.search_patients("")
        assert len(results) == len(all_patients)


# ── ReviewApplicationService tests ───────────────────────────────────────────


class TestReviewApplicationServiceComponent:
    SEEDED_CID = 1  # pre-seeded in consultation and generated_document repos

    @pytest.fixture
    def review_svc(self):
        consultation_repo = InMemoryConsultationRepository()
        doc_repo = InMemoryConsultationDocumentRepository()
        gen_repo = InMemoryGeneratedDocumentRepository()
        rx_repo = InMemoryPrescriptionRepository()
        patient_repo = InMemoryPatientRepository()
        email_svc = MockEmailService()

        # Add a consultation document for SEEDED_CID=1 (not pre-seeded in doc_repo)
        cid = self.SEEDED_CID
        doc_repo.save(_make_consultation_doc(cid=cid))

        return ReviewApplicationService(
            consultation_repository=consultation_repo,
            consultation_doc_repository=doc_repo,
            generated_repository=gen_repo,
            prescription_repository=rx_repo,
            patient_repository=patient_repo,
            email_service=email_svc,
        )

    def test_build_review_context_returns_three_items(self, review_svc):
        doc, gen, sr = review_svc.build_review_context(self.SEEDED_CID)
        assert doc is not None
        assert gen is not None
        assert sr is not None

    def test_build_review_context_with_speaker_turns(self, review_svc):
        doc, gen, sr = review_svc.build_review_context(self.SEEDED_CID)
        assert doc.normalized_transcript is not None
        turns = doc.normalized_transcript.cleaned_transcript
        assert len(turns) >= 1

    def test_approve_review_creates_prescription(self, review_svc):
        prescription = review_svc.approve_review(self.SEEDED_CID)
        assert prescription is not None
        assert prescription.consultation_id == self.SEEDED_CID

    def test_update_report_markdown(self, review_svc):
        new_md = "# Updated Report\n\nNew content."
        review_svc.update_report_markdown(self.SEEDED_CID, new_md)
        _, gen, _ = review_svc.build_review_context(self.SEEDED_CID)
        assert gen.generated_output.report_markdown == new_md

    def test_update_markdown_raises_for_missing_document(self, review_svc):
        with pytest.raises(ValueError, match="does not have a generated document"):
            review_svc.update_report_markdown(999, "# New content")


# ── PDF application service component test ───────────────────────────────────


class TestReportPdfApplicationServiceComponent:
    def test_generate_report_pdf_fails_without_orm_relationships(self):
        """PDF service requires ORM-loaded patient/clinician from the real DB.

        In-memory repos lack these relationships, so the service raises ValueError.
        This test documents that expected behaviour.
        """
        from app.application.pdf.services import ReportPdfApplicationService
        from app.infrastructure.persistence.in_memory.repositories import (
            InMemoryConsultationRepository,
            InMemoryGeneratedDocumentRepository,
            MockPdfGenerator,
        )

        consultation_repo = InMemoryConsultationRepository()
        gen_repo = InMemoryGeneratedDocumentRepository()

        # Overwrite the seeded doc for id=1 with one that has report_markdown
        gen_repo.save(_make_generated_doc(cid=1))

        svc = ReportPdfApplicationService(
            generated_repository=gen_repo,
            consultation_repository=consultation_repo,
            pdf_generator=MockPdfGenerator(),
        )
        # In-memory consultation has no .patient/.clinician ORM attrs → ValueError
        with pytest.raises((ValueError, AttributeError)):
            svc.generate_report_pdf(1)

    def test_generate_pdf_raises_when_no_document(self):
        from app.application.pdf.services import ReportPdfApplicationService
        from app.infrastructure.persistence.in_memory.repositories import (
            InMemoryConsultationRepository,
            InMemoryGeneratedDocumentRepository,
            MockPdfGenerator,
        )

        svc = ReportPdfApplicationService(
            generated_repository=InMemoryGeneratedDocumentRepository(),
            consultation_repository=InMemoryConsultationRepository(),
            pdf_generator=MockPdfGenerator(),
        )
        with pytest.raises(ValueError, match="No clinical report found"):
            svc.generate_report_pdf(999)
