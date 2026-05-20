"""In-memory repositories and placeholder adapters.

These mock implementations let the app boot without MySQL/MongoDB.
Once the real DB repositories are ready, swap them in via app/api/deps.py.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.domain.appointments.models import (
    Appointment,
    AppointmentCreateRequest,
    AppointmentRepository,
    AppointmentStatus,
)
from app.domain.audit.models import AuditLog, AuditLogRepository
from app.domain.auth.models import Staff, StaffRepository
from app.domain.email.models import (
    EmailMessage,
    EmailService,
    EmailTemplate,
    EmailTemplateRepository,
)
from app.domain.clinical_notes.models import (
    Assessment,
    ClinicalNoteGenerator,
    ClinicianApproval,
    ConsultationDocument,
    ConsultationDocumentRepository,
    EncounterInfo,
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
    ReviewOfSystems,
    SocialHistory,
    TranscriptDocument,
    TranscriptNormalizer,
    Vitals,
)
from app.domain.common.types import utcnow
from app.domain.consultations.models import (
    Consultation,
    ConsultationRepository,
    ConsultationStatus,
)
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
    Suggestion,
    SuggestionSeverity,
    SuggestionType,
    SuggestiveModeService,
    SuggestiveReview,
    SuggestiveReviewRequest,
)
from app.domain.transcriptions.models import (
    StreamingTranscriptChunk,
    StreamingTranscriptionService,
    TemporaryTranscriptChunk,
    TemporaryTranscriptChunkRepository,
    TranscriptResult,
    TranscriptionService,
)
from app.infrastructure.bootstrap.demo_transcripts import DEMO_CONSULTATION_TRANSCRIPTS


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

    def list_all(self) -> list[Staff]:
        return list(self._staff)

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
            Patient(
                id=5101,
                first_name="Ava",
                last_name="Miller",
                date_of_birth=date(1988, 5, 11),
                email="ava.miller@example.local",
                password_hash=_pw,
                gender="F",
                phone="+1 555 0101",
                allergies="No known drug allergies",
                medical_history="Mild seasonal allergies",
            ),
            Patient(
                id=5102,
                first_name="Noah",
                last_name="Perez",
                date_of_birth=date(1979, 2, 7),
                email="noah.perez@example.local",
                password_hash=_pw,
                gender="M",
                phone="+1 555 0102",
                allergies="No known drug allergies",
                medical_history="Hypertension treated with lisinopril",
            ),
            Patient(
                id=5103,
                first_name="Mia",
                last_name="Nguyen",
                date_of_birth=date(1995, 9, 3),
                email="mia.nguyen@example.local",
                password_hash=_pw,
                gender="F",
                phone="+1 555 0103",
                allergies="Penicillin allergy causing rash",
                medical_history="Recurrent sinus infections",
            ),
            Patient(
                id=5104,
                first_name="Luca",
                last_name="Reed",
                date_of_birth=date(2001, 12, 14),
                email="luca.reed@example.local",
                password_hash=_pw,
                gender="Other",
                phone="+1 555 0104",
                allergies="Not specified",
                medical_history="Not specified",
            ),
        ]
        self._next_id = 5105

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
            Consultation(
                id=4101,
                doctor_id=1,
                patient_id=5101,
                status=ConsultationStatus.PROCESSING,
                started_at=now,
            ),
            Consultation(
                id=4102,
                doctor_id=1,
                patient_id=5102,
                status=ConsultationStatus.PROCESSING,
                started_at=now,
            ),
            Consultation(
                id=4103,
                doctor_id=1,
                patient_id=5103,
                status=ConsultationStatus.PROCESSING,
                started_at=now,
            ),
            Consultation(
                id=4104,
                doctor_id=1,
                patient_id=5104,
                status=ConsultationStatus.PROCESSING,
                started_at=now,
            ),
        ]
        self._next_id = 4105

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
        now = utcnow()
        self._docs: dict[int, ConsultationDocument] = {
            consultation_id: ConsultationDocument(
                consultation_id=consultation_id,
                transcript=TranscriptDocument(full_text=transcript_text),
                created_at=now,
                updated_at=now,
            )
            for consultation_id, transcript_text in DEMO_CONSULTATION_TRANSCRIPTS.items()
        }

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
        return [
            chunk for chunk in self._chunks if chunk.consultation_id == consultation_id
        ]

    def delete_chunks_by_consultation(self, consultation_id: int) -> None:
        self._chunks = [
            chunk for chunk in self._chunks if chunk.consultation_id != consultation_id
        ]

    def delete_chunks_by_session(self, session_id: str) -> None:
        self._chunks = [
            chunk for chunk in self._chunks if chunk.session_id != session_id
        ]


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
                    report_markdown=(
                        "# Clinical Report\n\n"
                        "**Patient:** Giulia Rossi | **Age:** 36 | **Gender:** F\n\n"
                        "## Chief Complaint\nFollow-up hypertension\n\n"
                        "## Diagnosis\nEssential hypertension, controlled\n\n"
                        "## Medications\n- Lisinopril 10 mg once daily for 30 days (oral)\n\n"
                        "## Clinical Notes\nRoutine follow-up. BP controlled on current medication.\n"
                    ),
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
    def __init__(self) -> None:
        self._prompts = {prompt.id: prompt for prompt in self._seed_prompts()}

    @staticmethod
    def _seed_prompts() -> list[LlmPromptConfig]:
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
                id="clinical_report_generation_v3",
                prompt_name="Clinical Report Generation (Template Output)",
                model_target="qwen3:8b",
                temperature=0.2,
                max_tokens=2600,
                system_prompt=(
                    "Generate an English outpatient clinical report in JSON only. "
                    "Do not invent facts; use 'Not mentioned' or [] when missing."
                ),
                user_prompt_template=(
                    "Consultation {consultation_id}. Clinician: {clinician_name}. "
                    "Patient: {patient_name} ({patient_age}, {patient_gender}). "
                    "Transcript: {transcript_text}. Normalized: {normalized_transcript}. "
                    "Return JSON with keys patient_info, encounter_info, chief_complaint, "
                    "history_of_present_illness, review_of_systems, past_medical_history, "
                    "current_medications_mentioned, allergies, family_history, social_history, "
                    "vitals, examination_findings, assessment, diagnosis, medications, plan, "
                    "lab_tests_ordered, follow_up, patient_instructions, return_precautions, "
                    "clinical_notes_summary, missing_but_relevant_information, clinician_approval, "
                    "report_markdown (empty string)."
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
            LlmPromptConfig(
                id="suggestive_mode_v3",
                prompt_name="Suggestive Mode -- Clinical Safety Net v3",
                model_target="qwen3:8b",
                temperature=0.3,
                max_tokens=1500,
                system_prompt=(
                    "You are a second-pass outpatient clinical documentation safety reviewer. "
                    "Compare the generated clinical report and the normalized transcript. "
                    "Return only strict JSON. Use only evidence from the report or transcript. "
                    "Do not invent medical facts."
                ),
                user_prompt_template=(
                    "Consultation {consultation_id}. Generated report JSON: {generated_report}. "
                    "Normalized transcript JSON: {normalized_transcript}. "
                    "Return a JSON object with keys consultation_id, suggestions, "
                    "overall_risk_level, summary. Each suggestion must contain keys type, "
                    "severity, title, detail, recommendation, source_quote."
                ),
            ),
        ]

    def list_prompts(self) -> list[LlmPromptConfig]:
        return list(self._prompts.values())

    def get_by_id(self, prompt_id: str) -> LlmPromptConfig | None:
        return self._prompts.get(prompt_id)

    def save(self, prompt: LlmPromptConfig) -> LlmPromptConfig:
        self._prompts[prompt.id] = prompt
        return prompt


# ── email_templates (NoSQL mock) ───────────────────────────────────────


class InMemoryEmailTemplateRepository(EmailTemplateRepository):
    def __init__(self) -> None:
        self._templates = {template.id: template for template in self._seed_templates()}

    @staticmethod
    def _seed_templates() -> list[EmailTemplate]:
        return [
            EmailTemplate(
                id="prescription_delivery_v1",
                template_name="Prescription Delivery Email",
                subject_template="Your Prescription from Dr. {{doctor_name}}",
                body_template=(
                    "Hello {{patient_name}},\n\n"
                    "Your prescription from Dr. {{doctor_name}} is attached.\n\n"
                    "Regards,\nOPD-Vertex"
                ),
                placeholders=["patient_name", "doctor_name"],
                attachment_fields={"prescription_pdf": "required"},
            )
        ]

    def list_templates(self) -> list[EmailTemplate]:
        return list(self._templates.values())

    def get_by_id(self, template_id: str) -> EmailTemplate | None:
        return self._templates.get(template_id)

    def save(self, template: EmailTemplate) -> EmailTemplate:
        self._templates[template.id] = template
        return template


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
        self._entries: list[AuditLog] = []
        self._next_id = 1

    def list_recent(self) -> list[AuditLog]:
        return self._entries[-20:]

    def append(self, entry: AuditLog) -> AuditLog:
        entry.id = self._next_id
        self._next_id += 1
        self._entries.append(entry)
        return entry


# ── appointments ──────────────────────────────────────────────────────


def _strip_tz(dt: datetime) -> datetime:
    """Normalize to naive datetime so aware and naive values sort consistently."""
    return dt.replace(tzinfo=None) if dt and dt.tzinfo is not None else dt


class InMemoryAppointmentRepository(AppointmentRepository):
    def __init__(self) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC
        self._appointments: list[Appointment] = [
            Appointment(
                id=1,
                patient_id=1,
                doctor_id=1,
                scheduled_at=now,
                duration_minutes=30,
                status=AppointmentStatus.CONFIRMED,
                reason="Follow-up hypertension",
            ),
            Appointment(
                id=2,
                patient_id=2,
                doctor_id=1,
                scheduled_at=now,
                duration_minutes=30,
                status=AppointmentStatus.PENDING,
                reason="Annual check-up",
            ),
        ]
        self._next_id = 3

    @staticmethod
    def _status_priority(a: Appointment) -> tuple:
        order = {
            AppointmentStatus.CONFIRMED: 0,
            AppointmentStatus.PENDING: 1,
        }
        sched = _strip_tz(a.scheduled_at)
        fallback = _strip_tz(a.created_at) if a.created_at else sched
        return (order.get(a.status, 2), sched, fallback)

    def list_all(self) -> list[Appointment]:
        return sorted(self._appointments, key=self._status_priority)

    def get_by_id(self, appointment_id: int) -> Appointment | None:
        return next((a for a in self._appointments if a.id == appointment_id), None)

    def list_by_patient(self, patient_id: int) -> list[Appointment]:
        return sorted(
            [a for a in self._appointments if a.patient_id == patient_id],
            key=self._status_priority,
        )

    def list_by_doctor(self, doctor_id: int) -> list[Appointment]:
        return sorted(
            [a for a in self._appointments if a.doctor_id == doctor_id],
            key=self._status_priority,
        )

    def create(self, request: AppointmentCreateRequest) -> Appointment:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        appointment = Appointment(
            id=self._next_id,
            patient_id=request.patient_id,
            doctor_id=request.doctor_id,
            scheduled_at=_strip_tz(request.scheduled_at),  # always naive
            duration_minutes=request.duration_minutes,
            status=AppointmentStatus.PENDING,
            reason=request.reason,
            notes=request.notes,
            created_at=now,
            updated_at=now,
        )
        self._next_id += 1
        self._appointments.append(appointment)
        return appointment

    def update_status(
        self, appointment_id: int, status: AppointmentStatus
    ) -> Appointment | None:
        a = self.get_by_id(appointment_id)
        if a:
            a.status = status
        return a

    def cancel(self, appointment_id: int) -> Appointment | None:
        return self.update_status(appointment_id, AppointmentStatus.CANCELLED)

    def link_consultation(
        self, appointment_id: int, consultation_id: int
    ) -> Appointment | None:
        a = self.get_by_id(appointment_id)
        if a:
            a.consultation_id = consultation_id
        return a


# ── Mock services (transcription, LLM, suggestive, PDF, email) ────────


class MockTranscriptionService(TranscriptionService):
    def transcribe(self, consultation_id: int) -> TranscriptResult:
        return TranscriptResult(
            consultation_id=consultation_id,
            full_text="Mock transcript — replace with Faster-Whisper output.",
        )


class MockClinicalNoteGenerator(ClinicalNoteGenerator):
    _FIELD_MAP = {
        "chief complaint": "chief_complaint",
        "history of present illness": "history_of_present_illness",
        "ros general": "ros_general",
        "ros respiratory": "ros_respiratory",
        "ros cardiovascular": "ros_cardiovascular",
        "ros gastrointestinal": "ros_gastrointestinal",
        "ros neurological": "ros_neurological",
        "ros genitourinary": "ros_genitourinary",
        "ros musculoskeletal": "ros_musculoskeletal",
        "ros other": "ros_other",
        "past medical history": "past_medical_history",
        "current medications mentioned": "current_medications_mentioned",
        "allergies": "allergies",
        "family history": "family_history",
        "social smoking": "social_smoking",
        "social alcohol": "social_alcohol",
        "social substance use": "social_substance_use",
        "social occupation": "social_occupation",
        "vitals bp": "vitals_blood_pressure",
        "vitals hr": "vitals_heart_rate",
        "vitals temp": "vitals_temperature",
        "vitals rr": "vitals_respiratory_rate",
        "vitals spo2": "vitals_spo2",
        "vitals weight": "vitals_weight",
        "vitals height": "vitals_height",
        "vitals bmi": "vitals_bmi",
        "examination findings": "examination_findings",
        "primary diagnosis": "primary_diagnosis",
        "differential diagnoses": "differential_diagnoses",
        "clinical impression": "clinical_impression",
        "medications": "medications",
        "lab tests ordered": "lab_tests_ordered",
        "plan imaging": "plan_imaging",
        "plan referrals": "plan_referrals",
        "follow up": "follow_up",
        "patient instructions": "patient_instructions",
        "return precautions": "return_precautions",
        "clinical notes summary": "clinical_notes_summary",
        "missing but relevant information": "missing_but_relevant_information",
    }

    @staticmethod
    def _split_list(value: str) -> list[str]:
        return [item.strip() for item in value.split(";") if item.strip()]

    @staticmethod
    def _parse_medications(value: str) -> list[Medication]:
        medications: list[Medication] = []
        entries = [entry.strip() for entry in value.split(";") if entry.strip()]
        for entry in entries:
            parts = [part.strip() for part in entry.split("|")]
            if not parts:
                continue
            while len(parts) < 6:
                parts.append("")
            name, dosage, route, frequency, duration, special_instructions = parts[:6]
            if name.lower() == "none":
                continue
            medications.append(
                Medication(
                    name=name,
                    dosage=dosage or "Not specified",
                    route=route or "oral",
                    frequency=frequency or "Not specified",
                    duration=duration or "Not specified",
                    special_instructions=special_instructions or None,
                )
            )
        return medications

    @classmethod
    def _parse_structured_transcript(cls, transcript_text: str) -> dict[str, str]:
        fields: dict[str, str] = {}
        for raw_line in transcript_text.splitlines():
            line = raw_line.strip()
            if not line or ":" not in line:
                continue
            label, value = line.split(":", 1)
            normalized_label = cls._FIELD_MAP.get(label.strip().lower())
            if normalized_label is None:
                continue
            fields[normalized_label] = value.strip()
        return fields

    def generate(self, request) -> GeneratedClinicalNotes:
        parsed = self._parse_structured_transcript(request.transcript_text)
        if not parsed:
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

        medications = self._parse_medications(parsed.get("medications", ""))
        current_medications = self._split_list(
            parsed.get("current_medications_mentioned", "")
        )
        differential_diagnoses = self._split_list(
            parsed.get("differential_diagnoses", "")
        )
        lab_tests = self._split_list(parsed.get("lab_tests_ordered", ""))
        imaging = self._split_list(parsed.get("plan_imaging", ""))
        referrals = self._split_list(parsed.get("plan_referrals", ""))
        return_precautions = self._split_list(parsed.get("return_precautions", ""))
        missing_info = self._split_list(
            parsed.get("missing_but_relevant_information", "")
        )

        return GeneratedClinicalNotes(
            patient_info={
                "patient_id": str(request.patient_id),
                "doctor_id": str(request.doctor_id),
            },
            encounter_info=EncounterInfo(
                visit_type="Outpatient follow-up",
                consultation_mode="In person",
                information_reliability="Patient history considered reliable",
            ),
            chief_complaint=parsed.get("chief_complaint", "Mock complaint"),
            history_of_present_illness=parsed.get(
                "history_of_present_illness", "Not mentioned"
            ),
            review_of_systems=ReviewOfSystems(
                general=parsed.get("ros_general", ""),
                respiratory=parsed.get("ros_respiratory", ""),
                cardiovascular=parsed.get("ros_cardiovascular", ""),
                gastrointestinal=parsed.get("ros_gastrointestinal", ""),
                neurological=parsed.get("ros_neurological", ""),
                genitourinary=parsed.get("ros_genitourinary", ""),
                musculoskeletal=parsed.get("ros_musculoskeletal", ""),
                other=parsed.get("ros_other", ""),
            ),
            past_medical_history=parsed.get("past_medical_history", ""),
            current_medications_mentioned=current_medications,
            allergies=parsed.get("allergies", ""),
            family_history=parsed.get("family_history", ""),
            social_history=SocialHistory(
                smoking=parsed.get("social_smoking", ""),
                alcohol=parsed.get("social_alcohol", ""),
                substance_use=parsed.get("social_substance_use", ""),
                occupation=parsed.get("social_occupation", ""),
            ),
            vitals=Vitals(
                blood_pressure=parsed.get("vitals_blood_pressure", "Not recorded"),
                heart_rate=parsed.get("vitals_heart_rate", "Not recorded"),
                temperature=parsed.get("vitals_temperature", "Not recorded"),
                respiratory_rate=parsed.get("vitals_respiratory_rate", "Not recorded"),
                spo2=parsed.get("vitals_spo2", "Not recorded"),
                weight=parsed.get("vitals_weight", "Not recorded"),
                height=parsed.get("vitals_height", "Not recorded"),
                bmi=parsed.get("vitals_bmi", "Not recorded"),
            ),
            examination_findings=parsed.get("examination_findings", ""),
            assessment=Assessment(
                primary_diagnosis=parsed.get("primary_diagnosis", "Mock diagnosis"),
                differential_diagnoses=differential_diagnoses,
                clinical_impression=parsed.get("clinical_impression", ""),
            ),
            diagnosis=parsed.get("primary_diagnosis", "Mock diagnosis"),
            medications=medications,
            plan={
                "medications": medications,
                "lab_tests_ordered": lab_tests,
                "imaging_ordered": imaging,
                "referrals": referrals,
                "follow_up": parsed.get("follow_up", "Not specified"),
                "patient_instructions": parsed.get(
                    "patient_instructions", "No additional instructions provided."
                ),
            },
            lab_tests_ordered=lab_tests,
            follow_up=parsed.get("follow_up", "Not specified"),
            patient_instructions=parsed.get(
                "patient_instructions", "No additional instructions provided."
            ),
            return_precautions=return_precautions,
            clinician_approval=ClinicianApproval(
                status="Draft pending clinician approval",
            ),
            clinical_notes_summary=parsed.get(
                "clinical_notes_summary",
                (
                    "Generated from normalized transcript: "
                    f"{request.normalized_transcript.normalized_text[:40]}..."
                ),
            ),
            missing_but_relevant_information=missing_info,
        )


class MockSuggestiveModeService(SuggestiveModeService):
    @staticmethod
    def _contains_text(payload: object, needle: str) -> bool:
        return needle.lower() in str(payload).lower()

    @staticmethod
    def _extract_medication_names(generated_report: dict[str, object]) -> list[str]:
        medications = generated_report.get("medications", [])
        if not isinstance(medications, list):
            return []
        names: list[str] = []
        for medication in medications:
            if isinstance(medication, dict):
                name = str(medication.get("name", "")).strip()
                if name:
                    names.append(name.lower())
        return names

    def review(self, request: SuggestiveReviewRequest) -> SuggestiveReview:
        suggestions: list[Suggestion] = []
        generated_report = request.generated_report
        normalized_transcript = request.normalized_transcript or {}
        transcript_blob = f"{generated_report} {normalized_transcript}"

        medication_names = self._extract_medication_names(generated_report)
        allergies_text = str(generated_report.get("allergies", ""))
        diagnosis_text = str(generated_report.get("diagnosis", ""))
        missing_info = generated_report.get("missing_but_relevant_information", [])

        if "amoxicillin" in medication_names and self._contains_text(
            allergies_text, "penicillin"
        ):
            suggestions.append(
                Suggestion(
                    type=SuggestionType.CONTRAINDICATION,
                    severity=SuggestionSeverity.CRITICAL,
                    title="Penicillin allergy conflict",
                    detail=(
                        "The draft includes amoxicillin while the patient history documents "
                        "a penicillin allergy."
                    ),
                    recommendation=(
                        "Replace the antibiotic with a non-penicillin option and explicitly "
                        "document the allergy decision."
                    ),
                    source_quote="Penicillin allergy causing rash",
                )
            )

        if self._contains_text(
            transcript_blob, "orthostatic"
        ) and not self._contains_text(generated_report.get("follow_up", ""), "48"):
            suggestions.append(
                Suggestion(
                    type=SuggestionType.FOLLOW_UP,
                    severity=SuggestionSeverity.MEDIUM,
                    title="Follow-up interval may be too loose",
                    detail=(
                        "Orthostatic symptoms were documented, but the follow-up plan does not "
                        "clearly reinforce short-interval reassessment."
                    ),
                    recommendation=(
                        "Confirm a 24 to 48 hour follow-up window and ensure hydration and blood "
                        "pressure monitoring instructions are explicit."
                    ),
                    source_quote="Orthostatic dizziness likely related to mild dehydration.",
                )
            )

        if self._contains_text(diagnosis_text, "fatigue") and (
            isinstance(missing_info, list) and len(missing_info) > 0
        ):
            suggestions.append(
                Suggestion(
                    type=SuggestionType.OMISSION,
                    severity=SuggestionSeverity.MEDIUM,
                    title="Important fatigue workup details still missing",
                    detail=(
                        "The report acknowledges unresolved background information that may "
                        "change interpretation of persistent fatigue."
                    ),
                    recommendation=(
                        "Document baseline sleep duration, recent weight trend, and any menstrual "
                        "or dietary history if clinically relevant before final approval."
                    ),
                    source_quote=str(missing_info[0]),
                )
            )

        if self._contains_text(diagnosis_text, "sinusitis") and not self._contains_text(
            transcript_blob, "return precautions"
        ):
            suggestions.append(
                Suggestion(
                    type=SuggestionType.STANDARD_OF_CARE,
                    severity=SuggestionSeverity.LOW,
                    title="Return precautions should be explicit",
                    detail=(
                        "The sinusitis draft should clearly call out escalation symptoms such as "
                        "orbital swelling, high fever, or severe headache."
                    ),
                    recommendation=(
                        "Ensure red-flag precautions are visible in the final patient-facing plan."
                    ),
                    source_quote="Acute bacterial rhinosinusitis.",
                )
            )

        if suggestions:
            if any(
                item.severity == SuggestionSeverity.CRITICAL for item in suggestions
            ):
                risk_level = RiskLevel.RED
            elif any(
                item.severity in (SuggestionSeverity.HIGH, SuggestionSeverity.MEDIUM)
                for item in suggestions
            ):
                risk_level = RiskLevel.YELLOW
            else:
                risk_level = RiskLevel.GREEN
            summary = f"{len(suggestions)} issue(s) flagged for clinician review before approval."
        else:
            risk_level = RiskLevel.GREEN
            summary = "No significant clinical issues detected by the mock second-pass review."

        return SuggestiveReview(
            consultation_id=request.consultation_id,
            suggestions=suggestions,
            overall_risk_level=risk_level,
            summary=summary,
        )


class MockTranscriptNormalizer(TranscriptNormalizer):
    def normalize(self, request) -> NormalizedTranscript:
        """Return a mock normalized transcript with speaker-labeled turns."""
        import re

        raw = request.transcript_text or ""
        # Normalize whitespace first
        cleaned = re.sub(r"  +", " ", raw).strip()
        # Split the raw text into sentences and alternate DOCTOR/PATIENT
        sentences = [s.strip() for s in cleaned.split(".") if s.strip()]
        turns = []
        for i, sentence in enumerate(sentences):
            speaker = "DOCTOR" if i % 2 == 0 else "PATIENT"
            turns.append({"speaker": speaker, "utterance": sentence + "."})
        if not turns and cleaned:
            turns = [{"speaker": "UNKNOWN", "utterance": cleaned}]
        return NormalizedTranscript(
            raw_text=raw,
            cleaned_transcript=turns,
            normalization_notes=[
                "Mock normalization with alternating doctor/patient turns."
            ],
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
    def generate_report_pdf(self, report_markdown: str, consultation_metadata) -> str:
        import os
        import re
        from pathlib import Path
        import tempfile

        # Prefer configured pdf output dir so files are easy to find in the repo.
        try:
            from app.core.config import get_settings

            settings = get_settings()
            out_dir = Path(settings.pdf_output_dir)
        except Exception:
            out_dir = None

        from datetime import datetime as _dt

        def _pdf_filename(meta) -> str:
            last = (meta.patient_name or "unknown").strip().split()[-1]
            safe_last = re.sub(r"[^a-z0-9]", "", last.lower()) or "unknown"
            date_str = (
                meta.consultation_date.strftime("%Y%m%d")
                if meta.consultation_date
                else _dt.now().strftime("%Y%m%d")
            )
            return f"report_{safe_last}_{date_str}_{meta.consultation_id}.pdf"

        filename = _pdf_filename(consultation_metadata)

        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
            file_path = str(out_dir / filename)
        else:
            tmp_dir = tempfile.gettempdir()
            file_path = os.path.join(tmp_dir, filename)

        # Produce a styled PDF using the shared rendering helpers.
        try:
            from app.infrastructure.pdf.reportlab_adapter import (
                _build_banner,
                _build_info_card,
                _parse_content,
                _footer_cb,
            )
            from reportlab.platypus import SimpleDocTemplate, Spacer
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import inch

            usable_w = A4[0] - 1.5 * inch

            doc = SimpleDocTemplate(
                str(file_path),
                pagesize=A4,
                rightMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                topMargin=0.85 * inch,
                bottomMargin=0.85 * inch,
            )

            flowables = [
                _build_banner(consultation_metadata, usable_w),
                Spacer(1, 0.2 * inch),
                _build_info_card(consultation_metadata, usable_w),
                Spacer(1, 0.25 * inch),
                *_parse_content(report_markdown),
            ]

            doc.build(flowables, onFirstPage=_footer_cb, onLaterPages=_footer_cb)
            return file_path
        except Exception:
            # Fallback: write a minimal PDF so FileResponse can serve it
            import traceback

            traceback.print_exc()
            with open(file_path, "wb") as fh:
                fh.write(
                    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
                    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
                    b"xref\n0 4\n0000000000 65535 f \n"
                    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF\n"
                )
            return file_path

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


class MockStreamingTranscriptionService(StreamingTranscriptionService):
    """In-memory stub: accepts audio, returns empty transcript. No Whisper API needed."""

    def __init__(self) -> None:
        self._sessions: dict[str, int] = {}  # session_id -> consultation_id
        self._texts: dict[str, str] = {}  # session_id -> accumulated text

    def start_streaming(self, consultation_id: int) -> str:
        import uuid

        session_id = str(uuid.uuid4())
        self._sessions[session_id] = consultation_id
        self._texts[session_id] = ""
        return session_id

    def add_audio_chunk(
        self, session_id: str, audio_bytes: bytes
    ) -> StreamingTranscriptChunk | None:
        return None

    def finalize_session(self, session_id: str) -> TranscriptResult:
        consultation_id = self._sessions.get(session_id, 0)
        text = self._texts.get(session_id, "")
        self._sessions.pop(session_id, None)
        self._texts.pop(session_id, None)
        return TranscriptResult(
            consultation_id=consultation_id,
            full_text=text,
        )

    def get_current_text(self, session_id: str) -> str:
        return self._texts.get(session_id, "")

    def get_session_consultation_id(self, session_id: str) -> int:
        return self._sessions.get(session_id, 0)

    def get_completed_results(self, session_id: str) -> list[dict]:
        text = self._texts.get(session_id, "")
        return [{"text": text}] if text else []

    def inject_text(self, session_id: str, text: str) -> None:
        """Directly set transcript text (demo / no-mic mode)."""
        self._texts[session_id] = text


class MockEmailService(EmailService):
    def send_email(self, message: EmailMessage) -> dict:
        return {
            "status": "sent",
            "provider": "mock",
            "recipient": str(message.to_email),
            "subject": message.subject,
            "attachment_filename": (
                message.attachment.filename if message.attachment else None
            ),
            "message": "Mock email sent successfully",
        }

    def send_prescription_email(
        self, prescription_id: int, recipient_email: str
    ) -> str:
        return f"Prescription email sent to {recipient_email} for prescription {prescription_id}"
