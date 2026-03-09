"""In-memory repositories and placeholder adapters."""

from __future__ import annotations

from app.domain.audit.models import AuditLog, AuditLogRepository
from app.domain.auth.models import Staff, StaffRepository
from app.domain.clinical_notes.models import (
    ClinicalNoteGenerator,
    GeneratedClinicalNotes,
    GeneratedDocument,
    GeneratedDocumentRepository,
    LlmPromptConfig,
    Medication,
    PromptRepository,
)
from app.domain.common.types import generate_id
from app.domain.consultations.models import Consultation, ConsultationCreateRequest, ConsultationRepository, ConsultationStatus
from app.domain.email.models import EmailService, EmailTemplate, EmailTemplateRepository
from app.domain.patients.models import Patient, PatientCreateRequest, PatientRepository
from app.domain.pdf.models import PdfGenerator
from app.domain.prescriptions.models import Prescription, PrescriptionRepository
from app.domain.suggestive_mode.models import Suggestion, SuggestiveModeService, SuggestiveReview
from app.domain.transcription.models import TranscriptDocument, TranscriptDocumentRepository, TranscriptionService


class InMemoryStaffRepository(StaffRepository):
    def __init__(self) -> None:
        self._staff = [
            Staff(id="staff_001", username="doctor.demo", full_name="Dr. Ada Demo", role="doctor"),
            Staff(id="staff_002", username="admin.demo", full_name="Alex Admin", role="admin"),
        ]

    def get_by_username(self, username: str) -> Staff | None:
        return next((staff for staff in self._staff if staff.username == username), None)


class InMemoryPatientRepository(PatientRepository):
    def __init__(self) -> None:
        self._patients = [
            Patient(id="pat_001", first_name="Giulia", last_name="Rossi", email="giulia@example.local", phone="+39 0001", date_of_birth="1990-04-12"),
            Patient(id="pat_002", first_name="Marco", last_name="Bianchi", email="marco@example.local", phone="+39 0002", date_of_birth="1984-08-19"),
        ]

    def list_all(self) -> list[Patient]:
        return self._patients

    def get_by_id(self, patient_id: str) -> Patient | None:
        return next((patient for patient in self._patients if patient.id == patient_id), None)

    def create(self, payload: PatientCreateRequest) -> Patient:
        patient = Patient(id=generate_id("pat"), first_name=payload.first_name, last_name=payload.last_name, email=payload.email)
        self._patients.append(patient)
        return patient


class InMemoryConsultationRepository(ConsultationRepository):
    def __init__(self) -> None:
        self._consultations = [
            Consultation(id="con_001", patient_id="pat_001", clinician_id="staff_001", status=ConsultationStatus.REVIEW, chief_complaint="Follow-up hypertension"),
            Consultation(id="con_002", patient_id="pat_002", clinician_id="staff_001", status=ConsultationStatus.TRANSCRIBING, chief_complaint="Persistent cough"),
        ]

    def list_all(self) -> list[Consultation]:
        return self._consultations

    def get_by_id(self, consultation_id: str) -> Consultation | None:
        return next((consultation for consultation in self._consultations if consultation.id == consultation_id), None)

    def create(self, payload: ConsultationCreateRequest, clinician_id: str) -> Consultation:
        consultation = Consultation(
            id=generate_id("con"),
            patient_id=payload.patient_id,
            clinician_id=clinician_id,
            status=ConsultationStatus.RECORDING,
            chief_complaint=payload.chief_complaint,
        )
        self._consultations.append(consultation)
        return consultation


class InMemoryTranscriptRepository(TranscriptDocumentRepository):
    def __init__(self) -> None:
        self._transcripts = {
            "con_001": TranscriptDocument(id="trn_001", consultation_id="con_001", raw_text="Patient reports improved blood pressure control."),
            "con_002": TranscriptDocument(id="trn_002", consultation_id="con_002", raw_text="Mock transcript pending real speech-to-text pipeline."),
        }

    def get_by_consultation_id(self, consultation_id: str) -> TranscriptDocument | None:
        return self._transcripts.get(consultation_id)

    def save(self, transcript: TranscriptDocument) -> TranscriptDocument:
        self._transcripts[transcript.consultation_id] = transcript
        return transcript


class MockTranscriptionService(TranscriptionService):
    def __init__(self, repository: TranscriptDocumentRepository) -> None:
        self.repository = repository

    def transcribe(self, consultation_id: str) -> TranscriptDocument:
        transcript = TranscriptDocument(
            id=generate_id("trn"),
            consultation_id=consultation_id,
            raw_text="TODO: replace mock transcript with Faster-Whisper adapter output.",
        )
        return self.repository.save(transcript)


class InMemoryGeneratedDocumentRepository(GeneratedDocumentRepository):
    def __init__(self) -> None:
        self._documents = {
            "con_001": GeneratedDocument(
                id="gen_001",
                consultation_id="con_001",
                notes=GeneratedClinicalNotes(
                    subjective="Patient reports feeling better.",
                    objective="Vitals stable in placeholder workflow.",
                    assessment="Hypertension follow-up, stable.",
                    plan="Continue medication and review in four weeks.",
                    medications=[Medication(name="Lisinopril", dosage="10 mg", instructions="Once daily")],
                ),
                prescription_draft=[Medication(name="Lisinopril", dosage="10 mg", instructions="Once daily")],
            )
        }

    def get_by_consultation_id(self, consultation_id: str) -> GeneratedDocument | None:
        return self._documents.get(consultation_id)

    def save(self, document: GeneratedDocument) -> GeneratedDocument:
        self._documents[document.consultation_id] = document
        return document


class InMemoryPromptRepository(PromptRepository):
    def list_prompts(self) -> list[LlmPromptConfig]:
        return [
            LlmPromptConfig(
                id="prompt_soap",
                name="SOAP Draft",
                description="Base prompt for local note generation.",
                template="TODO: store real prompt text in MongoDB-backed repository.",
            )
        ]


class MockClinicalNoteGenerator(ClinicalNoteGenerator):
    def __init__(self, repository: GeneratedDocumentRepository) -> None:
        self.repository = repository

    def generate(self, consultation_id: str, transcript_text: str) -> GeneratedDocument:
        document = GeneratedDocument(
            id=generate_id("gen"),
            consultation_id=consultation_id,
            notes=GeneratedClinicalNotes(
                subjective="Generated from mock pipeline.",
                objective="No objective data captured yet.",
                assessment="Placeholder assessment.",
                plan=f"TODO: adapt clinical plan from transcript: {transcript_text[:40]}...",
            ),
        )
        return self.repository.save(document)


class MockSuggestiveModeService(SuggestiveModeService):
    def review(self, consultation_id: str, document_text: str) -> SuggestiveReview:
        return SuggestiveReview(
            consultation_id=consultation_id,
            suggestions=[Suggestion(code="TODO_REVIEW", severity="info", message="Suggestive mode placeholder active.")]
            if document_text
            else [],
        )


class InMemoryPrescriptionRepository(PrescriptionRepository):
    def __init__(self) -> None:
        self._prescriptions = [
            Prescription(
                id="rx_001",
                consultation_id="con_001",
                patient_id="pat_001",
                version=1,
                medications=[Medication(name="Lisinopril", dosage="10 mg", instructions="Once daily")],
                status="draft",
            )
        ]

    def list_all(self) -> list[Prescription]:
        return self._prescriptions

    def get_by_id(self, prescription_id: str) -> Prescription | None:
        return next((prescription for prescription in self._prescriptions if prescription.id == prescription_id), None)


class InMemoryAuditLogRepository(AuditLogRepository):
    def __init__(self) -> None:
        self._entries = [
            AuditLog(id="aud_001", actor_id="staff_001", action="view_dashboard", entity_type="dashboard", entity_id="root"),
        ]

    def list_recent(self) -> list[AuditLog]:
        return self._entries[-20:]

    def append(self, entry: AuditLog) -> AuditLog:
        self._entries.append(entry)
        return entry


class InMemoryEmailTemplateRepository(EmailTemplateRepository):
    def list_templates(self) -> list[EmailTemplate]:
        return [
            EmailTemplate(
                id="email_rx",
                name="prescription_delivery",
                subject="Your OPD-Vertex prescription",
                body="TODO: replace placeholder email template with a real editable version.",
            )
        ]


class MockPdfGenerator(PdfGenerator):
    def generate_prescription_pdf(self, prescription_id: str) -> str:
        return f"/tmp/{prescription_id}.pdf"


class MockEmailService(EmailService):
    def send_prescription_email(self, prescription_id: str, recipient: str) -> str:
        return f"Mock email queued for {recipient} with prescription {prescription_id}."
