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
    GeneratedDocumentRepository,
    LlmPromptConfig,
    PromptRepository,
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
)
from app.domain.transcription.models import TranscriptResult, TranscriptionService


# ── staff ──────────────────────────────────────────────────────────────


class InMemoryStaffRepository(StaffRepository):
    def __init__(self) -> None:
        self._staff = [
            Staff(
                id=1,
                first_name="Ada",
                last_name="Demo",
                email="doctor@example.local",
                password_hash="",
                specialization="General Medicine",
                license_number="LIC001",
                role="doctor",
            ),
            Staff(
                id=2,
                first_name="Alex",
                last_name="Admin",
                email="admin@example.local",
                password_hash="",
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
        self._patients = [
            Patient(
                id=1,
                first_name="Giulia",
                last_name="Rossi",
                date_of_birth=date(1990, 4, 12),
                email="giulia@example.local",
                gender="F",
                phone="+39 0001",
            ),
            Patient(
                id=2,
                first_name="Marco",
                last_name="Bianchi",
                date_of_birth=date(1984, 8, 19),
                email="marco@example.local",
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


# ── generated_documents (NoSQL mock) ───────────────────────────────────


class InMemoryGeneratedDocumentRepository(GeneratedDocumentRepository):
    def __init__(self) -> None:
        self._documents: dict[int, GeneratedDocument] = {
            1: GeneratedDocument(
                id="gen_001",
                consultation_id=1,
                doctor_id=1,
                patient_id=1,
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
                id="prescription_generation_v1",
                prompt_name="Prescription & Clinical Notes Generator",
                model_target="llama3.1-8b",
                temperature=0.2,
                max_tokens=2048,
            ),
            LlmPromptConfig(
                id="suggestive_mode_v1",
                prompt_name="Suggestive Mode -- Clinical Safety Net",
                model_target="llama3.1-8b",
                temperature=0.3,
                max_tokens=1500,
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
    def __init__(self, repository: GeneratedDocumentRepository) -> None:
        self.repository = repository

    def generate(self, consultation_id: int, transcript_text: str) -> GeneratedDocument:
        document = GeneratedDocument(
            consultation_id=consultation_id,
            doctor_id=1,
            patient_id=1,
            generated_output=GeneratedClinicalNotes(
                chief_complaint="Mock complaint",
                diagnosis="Mock diagnosis",
                clinical_notes_summary=f"Generated from: {transcript_text[:40]}...",
            ),
        )
        return self.repository.save(document)


class MockSuggestiveModeService(SuggestiveModeService):
    def review(self, consultation_id: int, document_json: str) -> SuggestiveReview:
        return SuggestiveReview(
            consultation_id=consultation_id,
            overall_risk_level=RiskLevel.GREEN,
            summary="No issues detected (mock).",
        )


class MockPdfGenerator(PdfGenerator):
    def generate_prescription_pdf(self, prescription_id: int) -> str:
        return f"/tmp/prescription_{prescription_id}.pdf"


class MockEmailService(EmailService):
    def send_prescription_email(self, prescription_id: int, recipient: str) -> str:
        return f"Mock email queued for {recipient} (prescription {prescription_id})."
