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
from app.infrastructure.db.mongo.connection import get_database
from app.infrastructure.db.mongo.repositories.mongo_repos import (
    MongoConsultationDocumentRepository,
    MongoEmailTemplateRepository,
    MongoGeneratedDocumentRepository,
    MongoPrescriptionArtifactRepository,
    MongoPromptRepository,
)
from fastapi import Request, HTTPException
from jose import jwt, JWTError
from app.core.security import SECRET_KEY, ALGORITHM

from app.application.transcriptions.services import TranscriptionApplicationService
from app.infrastructure.ai.transcription.faster_whisper_adapter import (
    StreamingFasterWhisperService,
)


def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        token = token.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def staff_repository() -> SqlStaffRepository:
    return SqlStaffRepository(get_session())


def patient_repository() -> SqlPatientRepository:
    return SqlPatientRepository(get_session())


def consultation_repository() -> SqlConsultationRepository:
    return SqlConsultationRepository(get_session())


@lru_cache
def consultation_doc_repository() -> MongoConsultationDocumentRepository:
    return MongoConsultationDocumentRepository(get_database())


@lru_cache
def generated_repository() -> MongoGeneratedDocumentRepository:
    return MongoGeneratedDocumentRepository(get_database())


def prescription_repository() -> SqlPrescriptionRepository:
    return SqlPrescriptionRepository(get_session())


def audit_repository() -> SqlAuditLogRepository:
    return SqlAuditLogRepository(get_session())


@lru_cache
def prompt_repository() -> MongoPromptRepository:
    return MongoPromptRepository(get_database())


@lru_cache
def email_template_repository() -> MongoEmailTemplateRepository:
    return MongoEmailTemplateRepository(get_database())


@lru_cache
def prescription_artifact_repository() -> MongoPrescriptionArtifactRepository:
    return MongoPrescriptionArtifactRepository(get_database())


@lru_cache
def auth_service() -> MockAuthService:
    return MockAuthService(staff_repository(), patient_repository())


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

@lru_cache
@lru_cache
def get_transcription_service() -> TranscriptionApplicationService:
    """Provide transcription service instance."""
    streaming_service = StreamingFasterWhisperService(
        model_size="base",
        device="cpu",
        chunk_duration=2.0,
    )
    return TranscriptionApplicationService(streaming_service=streaming_service)
