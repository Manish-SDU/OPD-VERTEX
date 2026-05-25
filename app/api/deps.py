"""Dependency wiring for mock and real adapters."""

from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException, Request
from jose import JWTError, jwt

from app.application.appointments.services import AppointmentApplicationService
from app.application.audit.services import AuditApplicationService
from app.application.auth.services import AuthApplicationService
from app.application.clinical_notes.services import (
    ClinicalNotesApplicationService,
    LlmHealthApplicationService,
    TranscriptNormalizationApplicationService,
)
from app.application.consultations.services import ConsultationApplicationService
from app.application.patients.services import PatientApplicationService
from app.application.pdf.services import ReportPdfApplicationService
from app.application.prescriptions.services import PrescriptionApplicationService
from app.application.review.services import ReviewApplicationService
from app.application.suggestive_mode.services import SuggestiveReviewApplicationService
from app.application.transcriptions.services import TranscriptionApplicationService
from app.infrastructure.email.smtp_sender import SmtpEmailService
from app.core.config import get_settings
from app.core.security import ALGORITHM, SECRET_KEY
from app.infrastructure.ai.llm.ollama_adapter import (
    OllamaClinicalNoteGenerator,
    OllamaHealthService,
    OllamaSuggestiveModeService,
    OllamaTranscriptNormalizer,
)
from app.infrastructure.ai.llm.ollama_client import OllamaClient
from app.infrastructure.auth.mock import MockAuthService
from app.infrastructure.pdf.reportlab_adapter import ReportLabPdfGenerator
from app.infrastructure.persistence.in_memory.repositories import (
    InMemoryAppointmentRepository,
    InMemoryAuditLogRepository,
    InMemoryConsultationDocumentRepository,
    InMemoryConsultationRepository,
    InMemoryEmailTemplateRepository,
    InMemoryGeneratedDocumentRepository,
    InMemoryPatientRepository,
    InMemoryPrescriptionArtifactRepository,
    InMemoryPrescriptionRepository,
    InMemoryPromptRepository,
    InMemoryStaffRepository,
    InMemoryTemporaryTranscriptChunkRepository,
    MockClinicalNoteGenerator,
    MockLlmHealthService,
    MockPdfGenerator,
    MockSuggestiveModeService,
    MockTranscriptNormalizer,
)


def _use_mock() -> bool:
    return get_settings().use_mock_adapters


def _decode_access_token(token: str | None) -> dict | None:
    if not token:
        return None
    try:
        token = token.replace("Bearer ", "")
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_optional_current_user(request: Request):
    return _decode_access_token(request.cookies.get("access_token"))


def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    payload = _decode_access_token(token)
    if payload is None:
        detail = "Not authenticated" if not token else "Invalid token"
        raise HTTPException(status_code=401, detail=detail)
    return payload


# ── Permission helpers ─────────────────────────────────────────────────


def is_patient(user: dict) -> bool:
    return user.get("role") == "patient"


def is_doctor(user: dict) -> bool:
    return user.get("role") == "doctor"


def is_admin(user: dict) -> bool:
    return user.get("role") == "admin"


def require_patient(user: dict) -> None:
    if not is_patient(user):
        raise HTTPException(status_code=403, detail="Patient access only")


def require_doctor(user: dict) -> None:
    if not is_doctor(user):
        raise HTTPException(status_code=403, detail="Doctor access only")


def require_admin(user: dict) -> None:
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin access only")


def require_doctor_or_admin(user: dict) -> None:
    """For operational (non-clinical) actions shared by doctors and admins."""
    if not (is_doctor(user) or is_admin(user)):
        raise HTTPException(status_code=403, detail="Doctor or admin access only")


def require_clinical_doctor(user: dict) -> None:
    """For doctor-only clinical actions: consultations, prescription approval, report editing."""
    if not is_doctor(user):
        raise HTTPException(
            status_code=403,
            detail="Clinical actions are restricted to doctors",
        )


@lru_cache
def _in_memory_staff_repo() -> InMemoryStaffRepository:
    return InMemoryStaffRepository()


@lru_cache
def _in_memory_patient_repo() -> InMemoryPatientRepository:
    return InMemoryPatientRepository()


@lru_cache
def _in_memory_consultation_repo() -> InMemoryConsultationRepository:
    return InMemoryConsultationRepository()


@lru_cache
def _in_memory_prescription_repo() -> InMemoryPrescriptionRepository:
    return InMemoryPrescriptionRepository()


@lru_cache
def _in_memory_audit_repo() -> InMemoryAuditLogRepository:
    return InMemoryAuditLogRepository()


@lru_cache
def _in_memory_consultation_doc_repo() -> InMemoryConsultationDocumentRepository:
    return InMemoryConsultationDocumentRepository()


@lru_cache
def _in_memory_generated_repo() -> InMemoryGeneratedDocumentRepository:
    return InMemoryGeneratedDocumentRepository()


@lru_cache
def _in_memory_prompt_repo() -> InMemoryPromptRepository:
    return InMemoryPromptRepository()


@lru_cache
def _in_memory_email_repo() -> InMemoryEmailTemplateRepository:
    return InMemoryEmailTemplateRepository()


@lru_cache
def _in_memory_prescription_artifact_repo() -> InMemoryPrescriptionArtifactRepository:
    return InMemoryPrescriptionArtifactRepository()


@lru_cache
def _in_memory_temp_chunk_repo() -> InMemoryTemporaryTranscriptChunkRepository:
    return InMemoryTemporaryTranscriptChunkRepository()


@lru_cache
def _mock_streaming_transcription_service():
    from app.infrastructure.persistence.in_memory.repositories import (
        MockStreamingTranscriptionService,
    )

    return MockStreamingTranscriptionService()


def staff_repository():
    if _use_mock():
        return _in_memory_staff_repo()
    from app.infrastructure.db.sql.connection import get_session
    from app.infrastructure.db.sql.repositories.sql_repos import SqlStaffRepository

    return SqlStaffRepository(get_session())


def patient_repository():
    if _use_mock():
        return _in_memory_patient_repo()
    from app.infrastructure.db.sql.connection import get_session
    from app.infrastructure.db.sql.repositories.sql_repos import SqlPatientRepository

    return SqlPatientRepository(get_session())


def consultation_repository():
    if _use_mock():
        return _in_memory_consultation_repo()
    from app.infrastructure.db.sql.connection import get_session
    from app.infrastructure.db.sql.repositories.sql_repos import (
        SqlConsultationRepository,
    )

    return SqlConsultationRepository(get_session())


def prescription_repository():
    if _use_mock():
        return _in_memory_prescription_repo()
    from app.infrastructure.db.sql.connection import get_session
    from app.infrastructure.db.sql.repositories.sql_repos import (
        SqlPrescriptionRepository,
    )

    return SqlPrescriptionRepository(get_session())


def audit_repository():
    if _use_mock():
        return _in_memory_audit_repo()
    from app.infrastructure.db.sql.connection import get_session
    from app.infrastructure.db.sql.repositories.sql_repos import SqlAuditLogRepository

    return SqlAuditLogRepository(get_session())


def consultation_doc_repository():
    if _use_mock():
        return _in_memory_consultation_doc_repo()
    from app.infrastructure.db.mongo.connection import get_database
    from app.infrastructure.db.mongo.repositories.mongo_repos import (
        MongoConsultationDocumentRepository,
    )

    return MongoConsultationDocumentRepository(get_database())


def generated_repository():
    if _use_mock():
        return _in_memory_generated_repo()
    from app.infrastructure.db.mongo.connection import get_database
    from app.infrastructure.db.mongo.repositories.mongo_repos import (
        MongoGeneratedDocumentRepository,
    )

    return MongoGeneratedDocumentRepository(get_database())


def prompt_repository():
    if _use_mock():
        return _in_memory_prompt_repo()
    from app.infrastructure.db.mongo.connection import get_database
    from app.infrastructure.db.mongo.repositories.mongo_repos import (
        MongoPromptRepository,
    )

    return MongoPromptRepository(get_database())


def email_template_repository():
    if _use_mock():
        return _in_memory_email_repo()
    from app.infrastructure.db.mongo.connection import get_database
    from app.infrastructure.db.mongo.repositories.mongo_repos import (
        MongoEmailTemplateRepository,
    )

    return MongoEmailTemplateRepository(get_database())


def prescription_artifact_repository():
    if _use_mock():
        return _in_memory_prescription_artifact_repo()
    from app.infrastructure.db.mongo.connection import get_database
    from app.infrastructure.db.mongo.repositories.mongo_repos import (
        MongoPrescriptionArtifactRepository,
    )

    return MongoPrescriptionArtifactRepository(get_database())


def temp_transcript_chunk_repository():
    if _use_mock():
        return _in_memory_temp_chunk_repo()
    from app.infrastructure.db.mongo.connection import get_database
    from app.infrastructure.db.mongo.repositories.mongo_repos import (
        MongoTemporaryTranscriptChunkRepository,
    )

    return MongoTemporaryTranscriptChunkRepository(get_database())


def auth_service() -> MockAuthService:
    return MockAuthService(staff_repository(), patient_repository())


@lru_cache
def transcription_normalizer():
    if _use_mock():
        return MockTranscriptNormalizer()
    return OllamaTranscriptNormalizer(ollama_client())


@lru_cache
def note_generator():
    if _use_mock():
        return MockClinicalNoteGenerator()
    return OllamaClinicalNoteGenerator(ollama_client())


@lru_cache
def suggestive_service():
    if _use_mock():
        return MockSuggestiveModeService()
    return OllamaSuggestiveModeService(ollama_client())


@lru_cache
def llm_health_service():
    if _use_mock():
        return MockLlmHealthService()
    return OllamaHealthService(ollama_client())


@lru_cache
def pdf_generator():
    if _use_mock():
        return MockPdfGenerator()
    return ReportLabPdfGenerator()


@lru_cache
def email_service():
    settings = get_settings()
    return SmtpEmailService(
        host=settings.smtp_host or "mailhog",
        port=settings.smtp_port or 1025,
        from_email=settings.smtp_from or "no-reply@example.local",
        from_name="OPD-Vertex",
        username=settings.smtp_user or "",
        password=settings.smtp_password or "",
    )


@lru_cache
def ollama_client() -> OllamaClient:
    settings = get_settings()
    return OllamaClient(
        base_url=settings.local_llm_endpoint,
        model_name=settings.llm_model_name,
        timeout_seconds=settings.ollama_timeout_seconds,
        max_retries=settings.ollama_max_retries,
    )


def get_auth_app_service() -> AuthApplicationService:
    return AuthApplicationService(auth_service())


def get_patient_app_service() -> PatientApplicationService:
    return PatientApplicationService(patient_repository())


def get_consultation_app_service() -> ConsultationApplicationService:
    return ConsultationApplicationService(consultation_repository())


def get_prescription_app_service() -> PrescriptionApplicationService:
    return PrescriptionApplicationService(prescription_repository())


def get_audit_app_service() -> AuditApplicationService:
    return AuditApplicationService(audit_repository())


def get_transcript_normalization_app_service() -> (
    TranscriptNormalizationApplicationService
):
    return TranscriptNormalizationApplicationService(
        consultation_doc_repository(),
        prompt_repository(),
        transcription_normalizer(),
    )


def get_clinical_notes_app_service() -> ClinicalNotesApplicationService:
    return ClinicalNotesApplicationService(
        consultation_repository(),
        consultation_doc_repository(),
        generated_repository(),
        prompt_repository(),
        patient_repository(),
        staff_repository(),
        get_transcript_normalization_app_service(),
        note_generator(),
    )


def get_suggestive_review_app_service() -> SuggestiveReviewApplicationService:
    return SuggestiveReviewApplicationService(
        consultation_repository(),
        consultation_doc_repository(),
        generated_repository(),
        prompt_repository(),
        suggestive_service(),
    )


def get_review_app_service() -> ReviewApplicationService:
    return ReviewApplicationService(
        consultation_repository(),
        consultation_doc_repository(),
        generated_repository(),
        prescription_repository(),
        patient_repository(),
        email_service(),
        get_report_pdf_app_service(),
    )


@lru_cache
def get_report_pdf_app_service() -> ReportPdfApplicationService:
    """Provides the Report PDF application service with dependencies."""
    import logging

    return ReportPdfApplicationService(
        generated_repository=generated_repository(),
        consultation_repository=consultation_repository(),
        pdf_generator=pdf_generator(),
        patient_repository=patient_repository(),
        staff_repository=staff_repository(),
        logger=logging.getLogger(__name__),
    )


def get_llm_health_app_service() -> LlmHealthApplicationService:
    return LlmHealthApplicationService(llm_health_service())


@lru_cache
def _in_memory_appointment_repo() -> InMemoryAppointmentRepository:
    return InMemoryAppointmentRepository()


def appointment_repository():
    if _use_mock():
        return _in_memory_appointment_repo()
    from app.infrastructure.db.sql.connection import get_session
    from app.infrastructure.db.sql.repositories.sql_repos import (
        SqlAppointmentRepository,
    )

    return SqlAppointmentRepository(get_session())


def get_appointment_app_service() -> AppointmentApplicationService:
    return AppointmentApplicationService(
        repository=appointment_repository(),
        consultation_repository=consultation_repository(),
    )


def get_transcription_service() -> TranscriptionApplicationService:
    settings = get_settings()
    use_mock_streaming = _use_mock() and not settings.use_real_whisper_streaming
    if use_mock_streaming:
        streaming_service = _mock_streaming_transcription_service()
    else:
        from app.infrastructure.ai.transcription.faster_whisper_adapter import (
            StreamingFasterWhisperService,
        )

        streaming_service = StreamingFasterWhisperService(
            model_size=settings.whisper_model_name,
            device="cpu",
            chunk_duration=2.0,
        )
    return TranscriptionApplicationService(
        streaming_service=streaming_service,
        temp_chunk_repo=temp_transcript_chunk_repository(),
        consultation_doc_repository=consultation_doc_repository(),
        consultation_repository=consultation_repository(),
    )
