"""In-memory repositories and placeholder adapters.

These mock implementations let the app boot without MySQL/MongoDB.
Once the real DB repositories are ready, swap them in via app/api/deps.py.
"""

from __future__ import annotations

from datetime import date

from app.domain.audit.models import AuditLog, AuditLogRepository
from app.domain.auth.models import Staff, StaffRepository
from app.domain.clinical_notes.models import (
    ClinicalNoteGenerator,
    ConsultationDocument,
    ConsultationDocumentRepository,
    GeneratedClinicalNotes,
    GeneratedDocument,
    GeneratedDocumentStatus,
    GeneratedDocumentRepository,
    LlmHealthStatus,
    LocalLlmHealthService,
    LlmPromptConfig,
    NormalizedTranscript,
    PrescriptionArtifact,
    PrescriptionArtifactRepository,
    PromptRepository,
    TranscriptNormalizer,
)
from app.domain.common.types import utcnow
from app.domain.consultations.models import (
    Consultation,
    ConsultationRepository,
    ConsultationStatus,
)
from app.domain.email.models import EmailService, EmailTemplate, EmailTemplateRepository
from app.domain.auth.models import StaffCreateRequest
from app.domain.patients.models import Patient, PatientCreateRequest, PatientRepository
from app.domain.pdf.models import PdfGenerator
from app.domain.prescriptions.models import (
    Medication,
    Prescription,
    PrescriptionRepository,
)
from app.domain.suggestive_mode.models import (
    RiskLevel,
    SuggestiveModeService,
    SuggestiveReview,
    SuggestiveReviewRequest,
)
from app.domain.transcriptions.models import (
    TemporaryTranscriptChunk,
    TemporaryTranscriptChunkRepository,
    TranscriptResult,
    TranscriptionService,
)


# ── staff ──────────────────────────────────────────────────────────────


class InMemoryStaffRepository(StaffRepository):
    def __init__(self) -> None:
        from app.core.security import hash_password

        _pw = hash_password("password")
        self._staff = [
            Staff(
                id=1,
                first_name="Ada",
                last_name="Demo",
                email="doctor@example.local",
                password_hash=_pw,
                specialization="General Medicine",
                license_number="LIC001",
                role="doctor",
            ),
            Staff(
                id=2,
                first_name="Alex",
                last_name="Admin",
                email="admin@example.local",
                password_hash=_pw,
                role="admin",
            ),
        ]

    def get_by_email(self, email: str) -> Staff | None:
        return next((s for s in self._staff if s.email == email), None)

    def get_by_id(self, staff_id: int) -> Staff | None:
        return next((s for s in self._staff if s.id == staff_id), None)

    def create(self, staff: StaffCreateRequest) -> Staff:
        new_id = max((s.id for s in self._staff), default=0) + 1
        new_staff = Staff(
            id=new_id,
            first_name=staff.first_name,
            last_name=staff.last_name,
            email=staff.email,
            password_hash=staff.password_hash,
            role=staff.role,
            specialization=staff.specialization,
            license_number=staff.license_number,
        )
        self._staff.append(new_staff)
        return new_staff


# ── patients ───────────────────────────────────────────────────────────


class InMemoryPatientRepository(PatientRepository):
    def __init__(self) -> None:
        from app.core.security import hash_password

        _pw = hash_password("password")
        self._patients = [
            Patient(
                id=1,
                first_name="Giulia",
                last_name="Rossi",
                date_of_birth=date(1990, 4, 12),
                email="giulia@example.local",
                password_hash=_pw,
                gender="F",
                phone="+39 0001",
            ),
            Patient(
                id=2,
                first_name="Marco",
                last_name="Bianchi",
                date_of_birth=date(1984, 8, 19),
                email="marco@example.local",
                password_hash=_pw,
                gender="M",
                phone="+39 0002",
            ),
        ]
        self._next_id = 3

    def list_all(self) -> list[Patient]:
        return self._patients

    def get_by_id(self, patient_id: int) -> Patient | None:
        return next((p for p in self._patients if p.id == patient_id), None)

    def get_by_email(self, email: str) -> Patient | None:
        return next((p for p in self._patients if p.email == email), None)

    def create(self, payload: PatientCreateRequest) -> Patient:
        patient = Patient(
            id=self._next_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            date_of_birth=payload.date_of_birth,
            email=payload.email,
            gender=payload.gender,
        )
        self._next_id += 1
        self._patients.append(patient)
        return patient


# ── consultations ──────────────────────────────────────────────────────


class InMemoryConsultationRepository(ConsultationRepository):
    def __init__(self) -> None:
        now = utcnow()
        self._consultations = [
            Consultation(
                id=1,
                doctor_id=1,
                patient_id=1,
                status=ConsultationStatus.REVIEW,
                started_at=now,
            ),
            Consultation(
                id=2,
                doctor_id=1,
                patient_id=2,
                status=ConsultationStatus.TRANSCRIBING,
                started_at=now,
            ),
        ]
        self._next_id = 3

    def list_all(self) -> list[Consultation]:
        return self._consultations

    def get_by_id(self, consultation_id: int) -> Consultation | None:
        return next((c for c in self._consultations if c.id == consultation_id), None)

    def create(self, consultation: Consultation) -> Consultation:
        consultation.id = self._next_id
        self._next_id += 1
        self._consultations.append(consultation)
        return consultation

    def update_status(self, consultation_id: int, status: ConsultationStatus) -> None:
        c = self.get_by_id(consultation_id)
        if c:
            c.status = status
            if status == ConsultationStatus.APPROVED:
                c.approved_at = utcnow()


# ── consultation_documents (NoSQL mock) ────────────────────────────────


class InMemoryConsultationDocumentRepository(ConsultationDocumentRepository):
    def __init__(self) -> None:
        self._docs: dict[int, ConsultationDocument] = {}

    def get_by_consultation_id(
        self, consultation_id: int
    ) -> ConsultationDocument | None:
        return self._docs.get(consultation_id)

    def save(self, document: ConsultationDocument) -> ConsultationDocument:
        self._docs[document.consultation_id] = document
        return document


class InMemoryPrescriptionArtifactRepository(PrescriptionArtifactRepository):
    def __init__(self) -> None:
        self._artifacts: dict[int, list[PrescriptionArtifact]] = {}
        self._next_id = 1

    def get_latest_by_prescription_id(
        self, prescription_id: int
    ) -> PrescriptionArtifact | None:
        artifacts = self._artifacts.get(prescription_id, [])
        return artifacts[-1] if artifacts else None

    def save(self, artifact: PrescriptionArtifact) -> PrescriptionArtifact:
        stored = artifact.model_copy(
            update={"id": artifact.id or f"artifact_{self._next_id}"}
        )
        if artifact.id is None:
            self._next_id += 1
        self._artifacts.setdefault(stored.prescription_id, []).append(stored)
        self._artifacts[stored.prescription_id].sort(key=lambda item: item.version)
        return stored


class InMemoryTemporaryTranscriptChunkRepository(TemporaryTranscriptChunkRepository):
    def __init__(self) -> None:
        self._chunks: list[TemporaryTranscriptChunk] = []

    def save_chunk(self, chunk: TemporaryTranscriptChunk) -> TemporaryTranscriptChunk:
        stored = chunk.model_copy(
            update={"id": chunk.id or f"chunk_{len(self._chunks) + 1}"}
        )
        self._chunks.append(stored)
        return stored

    def get_chunks_by_consultation(
        self, consultation_id: int
    ) -> list[TemporaryTranscriptChunk]:
        return [chunk for chunk in self._chunks if chunk.consultation_id == consultation_id]

    def delete_chunks_by_consultation(self, consultation_id: int) -> None:
        self._chunks = [
            chunk for chunk in self._chunks if chunk.consultation_id != consultation_id
        ]

    def delete_chunks_by_session(self, session_id: str) -> None:
        self._chunks = [chunk for chunk in self._chunks if chunk.session_id != session_id]


# ── generated_documents (NoSQL mock) ───────────────────────────────────


class InMemoryGeneratedDocumentRepository(GeneratedDocumentRepository):
    def __init__(self) -> None:
        self._documents: dict[int, GeneratedDocument] = {
            1: GeneratedDocument(
                id="gen_001",
                consultation_id=1,
                doctor_id=1,
                patient_id=1,
                status=GeneratedDocumentStatus.PENDING_REVIEW,
                generated_output=GeneratedClinicalNotes(
                    patient_info={"name": "Giulia Rossi", "age": "36", "gender": "F"},
                    chief_complaint="Follow-up hypertension",
                    diagnosis="Essential hypertension, controlled",
                    medications=[
                        Medication(
                            name="Lisinopril",
                            dosage="10 mg",
                            frequency="once daily",
                            duration="30 days",
                            route="oral",
                        )
                    ],
                    clinical_notes_summary="Routine follow-up. BP controlled on current medication.",
                ),
            ),
        }

    def get_by_consultation_id(self, consultation_id: int) -> GeneratedDocument | None:
        return self._documents.get(consultation_id)

    def save(self, document: GeneratedDocument) -> GeneratedDocument:
        self._documents[document.consultation_id] = document
        return document


# ── llm_prompts (NoSQL mock) ───────────────────────────────────────────


class InMemoryPromptRepository(PromptRepository):
    def list_prompts(self) -> list[LlmPromptConfig]:
        return [
            LlmPromptConfig(
                id="transcript_normalization_v1",
                prompt_name="Transcript Normalization",
                model_target="qwen3:8b",
                temperature=0.2,
                max_tokens=1400,
                system_prompt="Normalize transcripts into English JSON only.",
                user_prompt_template=(
                    "Return JSON with keys raw_text, normalized_text, chronology_notes, "
                    "removed_noise, unresolved_segments, language. "
                    "Consultation {consultation_id}. Transcript: {transcript_text}"
                ),
            ),
            LlmPromptConfig(
                id="clinical_report_generation_v2",
                prompt_name="Clinical Report Generation",
                model_target="qwen3:8b",
                temperature=0.2,
                max_tokens=2200,
                system_prompt="Generate a structured English medical report in JSON only.",
                user_prompt_template=(
                    "Return JSON with keys patient_info, chief_complaint, "
                    "history_of_present_illness, past_medical_history, allergies, vitals, "
                    "examination_findings, diagnosis, medications, lab_tests_ordered, "
                    "follow_up, patient_instructions, clinical_notes_summary. "
                    "Consultation {consultation_id}. Transcript: {transcript_text}. "
                    "Normalized transcript: {normalized_transcript}"
                ),
            ),
            LlmPromptConfig(
                id="suggestive_mode_v2",
                prompt_name="Suggestive Mode -- Clinical Safety Net",
                model_target="qwen3:8b",
                temperature=0.3,
                max_tokens=1500,
                system_prompt="Review clinical reports and return English JSON only.",
                user_prompt_template=(
                    "Return JSON with keys consultation_id, suggestions, "
                    "overall_risk_level, summary. Consultation {consultation_id}. "
                    "Report: {generated_report}. Normalized transcript: {normalized_transcript}"
                ),
            ),
        ]

    def get_by_id(self, prompt_id: str) -> LlmPromptConfig | None:
        return next((p for p in self.list_prompts() if p.id == prompt_id), None)


# ── email_templates (NoSQL mock) ───────────────────────────────────────


class InMemoryEmailTemplateRepository(EmailTemplateRepository):
    def list_templates(self) -> list[EmailTemplate]:
        return [
            EmailTemplate(
                id="prescription_delivery_v1",
                template_name="Prescription Delivery Email",
                subject_template="Your Prescription from Dr. {{doctor_name}}",
                body_template="placeholder body",
            )
        ]

    def get_by_id(self, template_id: str) -> EmailTemplate | None:
        return next((t for t in self.list_templates() if t.id == template_id), None)


# ── prescriptions ──────────────────────────────────────────────────────


class InMemoryPrescriptionRepository(PrescriptionRepository):
    def __init__(self) -> None:
        self._prescriptions = [
            Prescription(
                id=1,
                consultation_id=1,
                doctor_id=1,
                patient_id=1,
                diagnosis="Essential hypertension, controlled",
                medications=[
                    Medication(
                        name="Lisinopril",
                        dosage="10 mg",
                        frequency="once daily",
                        duration="30 days",
                        route="oral",
                    )
                ],
                is_approved=True,
                version=1,
            )
        ]
        self._next_id = 2

    def list_all(self) -> list[Prescription]:
        return self._prescriptions

    def get_by_id(self, prescription_id: int) -> Prescription | None:
        return next((p for p in self._prescriptions if p.id == prescription_id), None)

    def create(self, prescription: Prescription) -> Prescription:
        prescription.id = self._next_id
        self._next_id += 1
        self._prescriptions.append(prescription)
        return prescription


# ── audit_logs ─────────────────────────────────────────────────────────


class InMemoryAuditLogRepository(AuditLogRepository):
    def __init__(self) -> None:
        self._entries = [
            AuditLog(
                id=1,
                user_id=1,
                user_role="doctor",
                action="LOGIN",
                target_table="staff",
                target_id=1,
            ),
        ]
        self._next_id = 2

    def list_recent(self) -> list[AuditLog]:
        return self._entries[-20:]

    def append(self, entry: AuditLog) -> AuditLog:
        entry.id = self._next_id
        self._next_id += 1
        self._entries.append(entry)
        return entry


# ── Mock services (transcription, LLM, suggestive, PDF, email) ────────


class MockTranscriptionService(TranscriptionService):
    def transcribe(self, consultation_id: int) -> TranscriptResult:
        return TranscriptResult(
            consultation_id=consultation_id,
            full_text="Mock transcript — replace with Faster-Whisper output.",
        )


class MockClinicalNoteGenerator(ClinicalNoteGenerator):
    def generate(self, request) -> GeneratedClinicalNotes:
        return GeneratedClinicalNotes(
            patient_info={
                "patient_id": str(request.patient_id),
                "doctor_id": str(request.doctor_id),
            },
            chief_complaint="Mock complaint",
            diagnosis="Mock diagnosis",
            follow_up="Not specified",
            patient_instructions="No additional instructions provided.",
            clinical_notes_summary=(
                "Generated from normalized transcript: "
                f"{request.normalized_transcript.normalized_text[:40]}..."
            ),
        )


class MockSuggestiveModeService(SuggestiveModeService):
    def review(self, request: SuggestiveReviewRequest) -> SuggestiveReview:
        return SuggestiveReview(
            consultation_id=request.consultation_id,
            overall_risk_level=RiskLevel.GREEN,
            summary="No issues detected (mock).",
        )


class MockTranscriptNormalizer(TranscriptNormalizer):
    def normalize(self, request) -> NormalizedTranscript:
        cleaned = " ".join(request.transcript_text.split())
        return NormalizedTranscript(
            raw_text=request.transcript_text,
            normalized_text=cleaned,
            chronology_notes=["Mock normalization preserved chronology."],
            removed_noise=[],
            unresolved_segments=[],
            language="en",
        )


class MockLlmHealthService(LocalLlmHealthService):
    def check_health(self) -> LlmHealthStatus:
        return LlmHealthStatus(
            base_url="http://localhost:11434",
            model_name="qwen3:8b",
            ollama_reachable=True,
            model_available=True,
            healthy=True,
            detail="Mock LLM health check.",
        )


class MockPdfGenerator(PdfGenerator):
    def generate_prescription_pdf(
        self, prescription: Prescription
    ) -> PrescriptionArtifact:
        return PrescriptionArtifact(
            prescription_id=prescription.id or 0,
            consultation_id=prescription.consultation_id,
            doctor_id=prescription.doctor_id,
            patient_id=prescription.patient_id,
            version=prescription.version,
            storage_backend="mongo_metadata",
            file_name=f"prescription_{prescription.id or 'draft'}.pdf",
            byte_size=0,
        )


class MockEmailService(EmailService):
    def send_prescription_email(self, prescription_id: int, recipient: str) -> str:
        return f"Mock email queued for {recipient} (prescription {prescription_id})."
