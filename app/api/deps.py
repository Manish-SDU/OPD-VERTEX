"""Dependency wiring for placeholder adapters.

When the real DB repositories are ready, swap InMemory* classes
for Sql*/Mongo* classes here. The rest of the app stays unchanged.
"""

from __future__ import annotations

from functools import lru_cache

from app.application.audit.services import AuditApplicationService
from app.application.auth.services import AuthApplicationService
from app.application.consultations.services import ConsultationApplicationService
from app.application.patients.services import PatientApplicationService
from app.application.prescriptions.services import PrescriptionApplicationService
from app.application.review.services import ReviewApplicationService
from app.infrastructure.auth.mock import MockAuthService
from app.infrastructure.persistence.in_memory.repositories import (
    InMemoryConsultationDocumentRepository,
    InMemoryEmailTemplateRepository,
    InMemoryGeneratedDocumentRepository,
    InMemoryPromptRepository,
    MockClinicalNoteGenerator,
    MockEmailService,
    MockPdfGenerator,
    MockSuggestiveModeService,
    MockTranscriptionService,
)
from app.infrastructure.db.sql.repositories.sql_repos import (
    SqlStaffRepository,
    SqlPatientRepository,
    SqlConsultationRepository,
    SqlPrescriptionRepository,
    SqlAuditLogRepository,
)
from app.infrastructure.db.sql.connection import get_session


def staff_repository() -> SqlStaffRepository:
    return SqlStaffRepository(get_session())


def patient_repository() -> SqlPatientRepository:
    return SqlPatientRepository(get_session())


def consultation_repository() -> SqlConsultationRepository:
    return SqlConsultationRepository(get_session())


@lru_cache
def consultation_doc_repository() -> InMemoryConsultationDocumentRepository:
    return InMemoryConsultationDocumentRepository()


@lru_cache
def generated_repository() -> InMemoryGeneratedDocumentRepository:
    return InMemoryGeneratedDocumentRepository()


def prescription_repository() -> SqlPrescriptionRepository:
    return SqlPrescriptionRepository(get_session())


def audit_repository() -> SqlAuditLogRepository:
    return SqlAuditLogRepository(get_session())


@lru_cache
def prompt_repository() -> InMemoryPromptRepository:
    return InMemoryPromptRepository()


@lru_cache
def email_template_repository() -> InMemoryEmailTemplateRepository:
    return InMemoryEmailTemplateRepository()


@lru_cache
def auth_service() -> MockAuthService:
    return MockAuthService(staff_repository())


@lru_cache
def transcription_service() -> MockTranscriptionService:
    return MockTranscriptionService()


@lru_cache
def note_generator() -> MockClinicalNoteGenerator:
    return MockClinicalNoteGenerator(generated_repository())


@lru_cache
def suggestive_service() -> MockSuggestiveModeService:
    return MockSuggestiveModeService()


@lru_cache
def pdf_generator() -> MockPdfGenerator:
    return MockPdfGenerator()


@lru_cache
def email_service() -> MockEmailService:
    return MockEmailService()


def get_auth_app_service() -> AuthApplicationService:
    return AuthApplicationService(auth_service())


def get_patient_app_service() -> PatientApplicationService:
    return PatientApplicationService(patient_repository())


def get_consultation_app_service() -> ConsultationApplicationService:
    return ConsultationApplicationService(consultation_repository())


def get_review_app_service() -> ReviewApplicationService:
    return ReviewApplicationService(
        consultation_doc_repository(),
        generated_repository(),
        transcription_service(),
        note_generator(),
        suggestive_service(),
    )


def get_prescription_app_service() -> PrescriptionApplicationService:
    return PrescriptionApplicationService(prescription_repository())


def get_audit_app_service() -> AuditApplicationService:
    return AuditApplicationService(audit_repository())
