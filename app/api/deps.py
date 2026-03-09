"""Dependency wiring for placeholder adapters."""

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
    InMemoryAuditLogRepository,
    InMemoryConsultationRepository,
    InMemoryEmailTemplateRepository,
    InMemoryGeneratedDocumentRepository,
    InMemoryPatientRepository,
    InMemoryPrescriptionRepository,
    InMemoryPromptRepository,
    InMemoryStaffRepository,
    InMemoryTranscriptRepository,
    MockClinicalNoteGenerator,
    MockEmailService,
    MockPdfGenerator,
    MockSuggestiveModeService,
    MockTranscriptionService,
)


@lru_cache
def staff_repository() -> InMemoryStaffRepository:
    return InMemoryStaffRepository()


@lru_cache
def patient_repository() -> InMemoryPatientRepository:
    return InMemoryPatientRepository()


@lru_cache
def consultation_repository() -> InMemoryConsultationRepository:
    return InMemoryConsultationRepository()


@lru_cache
def transcript_repository() -> InMemoryTranscriptRepository:
    return InMemoryTranscriptRepository()


@lru_cache
def generated_repository() -> InMemoryGeneratedDocumentRepository:
    return InMemoryGeneratedDocumentRepository()


@lru_cache
def prescription_repository() -> InMemoryPrescriptionRepository:
    return InMemoryPrescriptionRepository()


@lru_cache
def audit_repository() -> InMemoryAuditLogRepository:
    return InMemoryAuditLogRepository()


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
    return MockTranscriptionService(transcript_repository())


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
        transcript_repository(),
        generated_repository(),
        transcription_service(),
        note_generator(),
        suggestive_service(),
    )


def get_prescription_app_service() -> PrescriptionApplicationService:
    return PrescriptionApplicationService(prescription_repository())


def get_audit_app_service() -> AuditApplicationService:
    return AuditApplicationService(audit_repository())
