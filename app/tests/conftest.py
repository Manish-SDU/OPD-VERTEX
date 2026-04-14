"""Shared fixtures for all tests.

Provides in-memory repositories and service instances so that tests
run without MySQL/MongoDB connections.
"""

from __future__ import annotations

import pytest

from app.infrastructure.persistence.in_memory.repositories import (
    InMemoryAuditLogRepository,
    InMemoryConsultationDocumentRepository,
    InMemoryConsultationRepository,
    InMemoryEmailTemplateRepository,
    InMemoryGeneratedDocumentRepository,
    InMemoryPatientRepository,
    InMemoryPrescriptionArtifactRepository,
    InMemoryPromptRepository,
    InMemoryPrescriptionRepository,
    InMemoryStaffRepository,
    MockClinicalNoteGenerator,
    MockEmailService,
    MockLlmHealthService,
    MockPdfGenerator,
    MockSuggestiveModeService,
    MockTranscriptNormalizer,
    MockTranscriptionService,
)
from app.infrastructure.auth.mock import MockAuthService
from app.application.audit.services import AuditApplicationService
from app.application.auth.services import AuthApplicationService
from app.application.clinical_notes.services import (
    ClinicalNotesApplicationService,
    TranscriptNormalizationApplicationService,
)
from app.application.consultations.services import ConsultationApplicationService
from app.application.patients.services import PatientApplicationService
from app.application.prescriptions.services import PrescriptionApplicationService
from app.application.review.services import ReviewApplicationService
from app.application.suggestive_mode.services import SuggestiveReviewApplicationService


# ── Repository fixtures ────────────────────────────────────────────────


@pytest.fixture
def staff_repo():
    return InMemoryStaffRepository()


@pytest.fixture
def patient_repo():
    return InMemoryPatientRepository()


@pytest.fixture
def consultation_repo():
    return InMemoryConsultationRepository()


@pytest.fixture
def consultation_doc_repo():
    return InMemoryConsultationDocumentRepository()


@pytest.fixture
def generated_doc_repo():
    return InMemoryGeneratedDocumentRepository()


@pytest.fixture
def prescription_artifact_repo():
    return InMemoryPrescriptionArtifactRepository()


@pytest.fixture
def prescription_repo():
    return InMemoryPrescriptionRepository()


@pytest.fixture
def audit_repo():
    return InMemoryAuditLogRepository()


@pytest.fixture
def prompt_repo():
    return InMemoryPromptRepository()


@pytest.fixture
def email_template_repo():
    return InMemoryEmailTemplateRepository()


# ── Mock service fixtures ──────────────────────────────────────────────


@pytest.fixture
def mock_auth_service(staff_repo, patient_repo):
    return MockAuthService(staff_repo, patient_repo)


@pytest.fixture
def transcription_service():
    return MockTranscriptionService()


@pytest.fixture
def note_generator():
    return MockClinicalNoteGenerator()


@pytest.fixture
def suggestive_service():
    return MockSuggestiveModeService()


@pytest.fixture
def transcript_normalizer():
    return MockTranscriptNormalizer()


@pytest.fixture
def llm_health_service():
    return MockLlmHealthService()


@pytest.fixture
def pdf_generator():
    return MockPdfGenerator()


@pytest.fixture
def email_service():
    return MockEmailService()


# ── Application service fixtures ───────────────────────────────────────


@pytest.fixture
def auth_app_service(mock_auth_service):
    return AuthApplicationService(mock_auth_service)


@pytest.fixture
def patient_app_service(patient_repo):
    return PatientApplicationService(patient_repo)


@pytest.fixture
def consultation_app_service(consultation_repo):
    return ConsultationApplicationService(consultation_repo)


@pytest.fixture
def prescription_app_service(prescription_repo):
    return PrescriptionApplicationService(prescription_repo)


@pytest.fixture
def audit_app_service(audit_repo):
    return AuditApplicationService(audit_repo)


@pytest.fixture
def review_app_service(
    consultation_doc_repo,
    generated_doc_repo,
    consultation_repo,
    prescription_repo,
):
    return ReviewApplicationService(
        consultation_repo,
        consultation_doc_repo,
        generated_doc_repo,
        prescription_repo,
    )


@pytest.fixture
def transcript_normalization_app_service(
    consultation_doc_repo, prompt_repo, transcript_normalizer
):
    return TranscriptNormalizationApplicationService(
        consultation_doc_repo,
        prompt_repo,
        transcript_normalizer,
    )


@pytest.fixture
def clinical_notes_app_service(
    consultation_repo,
    consultation_doc_repo,
    generated_doc_repo,
    prompt_repo,
    transcript_normalization_app_service,
    note_generator,
):
    return ClinicalNotesApplicationService(
        consultation_repo,
        consultation_doc_repo,
        generated_doc_repo,
        prompt_repo,
        transcript_normalization_app_service,
        note_generator,
    )


@pytest.fixture
def suggestive_review_app_service(
    consultation_repo,
    consultation_doc_repo,
    generated_doc_repo,
    prompt_repo,
    suggestive_service,
):
    return SuggestiveReviewApplicationService(
        consultation_repo,
        consultation_doc_repo,
        generated_doc_repo,
        prompt_repo,
        suggestive_service,
    )
