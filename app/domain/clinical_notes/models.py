"""Clinical note generation domain contracts.

Maps to MongoDB collections: generated_documents, consultation_documents, llm_prompts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.domain.prescriptions.models import Medication
from app.domain.suggestive_mode.models import SuggestiveReview


# --- Vitals sub-model --------------------------------------------------


class Vitals(BaseModel):
    blood_pressure: str = "Not recorded"
    heart_rate: str = "Not recorded"
    temperature: str = "Not recorded"
    respiratory_rate: str = "Not recorded"
    spo2: str = "Not recorded"
    weight: str = "Not recorded"
    height: str = "Not recorded"
    bmi: str = "Not recorded"


class SpeakerTurn(BaseModel):
    """A single speaker turn in a normalized transcript."""

    speaker: str  # DOCTOR | PATIENT | UNKNOWN
    utterance: str


class NormalizedTranscript(BaseModel):
    """LLM-cleaned transcript that preserves meaning and chronology.

    The LLM returns cleaned_transcript (speaker-labeled turns).  We keep the
    raw_text / normalized_text fields for backwards-compatibility with any code
    that still reads the flat string form; normalized_text is auto-derived.
    """

    raw_text: str = ""
    # Speaker-labeled turns as produced by the normalization prompt
    cleaned_transcript: list[SpeakerTurn] = Field(default_factory=list)
    uncertain_segments: list[dict] = Field(default_factory=list)
    normalization_notes: list[str] = Field(default_factory=list)
    # Derived flat text kept for backward-compat
    normalized_text: str = ""
    chronology_notes: list[str] = Field(default_factory=list)
    removed_noise: list[str] = Field(default_factory=list)
    unresolved_segments: list[str] = Field(default_factory=list)
    language: str = "en"

    @field_validator(
        "chronology_notes",
        "removed_noise",
        "unresolved_segments",
        "normalization_notes",
        mode="before",
    )
    @classmethod
    def _coerce_string_lists(cls, value):
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return []
            return [cleaned]
        return value

    @field_validator("cleaned_transcript", mode="before")
    @classmethod
    def _coerce_cleaned_transcript(cls, value):
        if value is None:
            return []
        if isinstance(value, list):
            result = []
            for item in value:
                if isinstance(item, SpeakerTurn):
                    result.append(item)
                elif isinstance(item, dict):
                    speaker = item.get("speaker", "UNKNOWN")
                    utterance = item.get("utterance", item.get("text", ""))
                    if utterance:
                        result.append(SpeakerTurn(speaker=speaker, utterance=utterance))
            return result
        return []

    def model_post_init(self, __context) -> None:
        """Derive normalized_text from cleaned_transcript if not set."""
        if not self.normalized_text and self.cleaned_transcript:
            self.normalized_text = "\n".join(
                f"{turn.speaker}: {turn.utterance}" for turn in self.cleaned_transcript
            )


class LlmExecutionMetadata(BaseModel):
    provider: str = "ollama"
    model_name: str = "qwen3:8b"
    prompt_id: str = ""
    prompt_version: int = 1
    temperature: float = 0.2
    max_tokens: int = 2048
    generated_at: datetime | None = None
    raw_response_excerpt: str = ""


class LlmHealthStatus(BaseModel):
    provider: str = "ollama"
    base_url: str
    model_name: str
    ollama_reachable: bool = False
    model_available: bool = False
    healthy: bool = False
    detail: str = ""


# --- Generated clinical notes (LLM output) -----------------------------


class Assessment(BaseModel):
    primary_diagnosis: str = ""
    differential_diagnoses: list[str] = Field(default_factory=list)
    clinical_impression: str = ""

    @field_validator("differential_diagnoses", mode="before")
    @classmethod
    def _coerce_differentials(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            cleaned = value.strip()
            return [cleaned] if cleaned else []
        return value


class Plan(BaseModel):
    medications: list[Medication] = Field(default_factory=list)
    lab_tests_ordered: list[str] = Field(default_factory=list)
    imaging_ordered: list[str] = Field(default_factory=list)
    referrals: list[str] = Field(default_factory=list)
    follow_up: str = ""
    patient_instructions: str = ""

    @field_validator(
        "lab_tests_ordered",
        "imaging_ordered",
        "referrals",
        mode="before",
    )
    @classmethod
    def _coerce_string_list_fields(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            cleaned = value.strip()
            return [cleaned] if cleaned else []
        return value


class EncounterInfo(BaseModel):
    encounter_id: str = ""
    date: str = ""
    time: str = ""
    visit_type: str = ""
    clinician_name: str = ""
    consultation_mode: str = ""
    accompanied_by: str = ""
    primary_language: str = ""
    information_reliability: str = ""


class ReviewOfSystems(BaseModel):
    general: str = ""
    respiratory: str = ""
    cardiovascular: str = ""
    gastrointestinal: str = ""
    neurological: str = ""
    genitourinary: str = ""
    musculoskeletal: str = ""
    other: str = ""


class SocialHistory(BaseModel):
    smoking: str = ""
    alcohol: str = ""
    substance_use: str = ""
    occupation: str = ""


class ClinicianApproval(BaseModel):
    status: str = ""
    reviewed_by: str = ""
    reviewed_at: str = ""


class GeneratedClinicalNotes(BaseModel):
    """Structure returned by the Prescription & Clinical Notes Generator prompt."""

    patient_info: dict[str, str] = Field(default_factory=dict)
    encounter_info: EncounterInfo = Field(default_factory=EncounterInfo)

    chief_complaint: str = ""
    history_of_present_illness: str = ""
    review_of_systems: ReviewOfSystems = Field(default_factory=ReviewOfSystems)

    past_medical_history: str = ""
    current_medications_mentioned: list[str] = Field(default_factory=list)

    allergies: str = ""
    family_history: str = ""
    social_history: SocialHistory = Field(default_factory=SocialHistory)

    vitals: Vitals = Field(default_factory=Vitals)
    examination_findings: str = ""

    assessment: Assessment = Field(default_factory=Assessment)
    diagnosis: str = ""

    medications: list[Medication] = Field(default_factory=list)
    plan: Plan = Field(default_factory=Plan)

    lab_tests_ordered: list[str] = Field(default_factory=list)
    follow_up: str = ""
    patient_instructions: str = ""

    return_precautions: list[str] = Field(default_factory=list)
    clinician_approval: ClinicianApproval = Field(default_factory=ClinicianApproval)

    clinical_notes_summary: str = ""
    missing_but_relevant_information: list[str] = Field(default_factory=list)

    report_markdown: str = ""

    @field_validator(
        "chief_complaint",
        "history_of_present_illness",
        "past_medical_history",
        "allergies",
        "family_history",
        "examination_findings",
        "diagnosis",
        "follow_up",
        "patient_instructions",
        "clinical_notes_summary",
        "report_markdown",
        mode="before",
    )
    @classmethod
    def _coerce_none_to_str(cls, value):
        if value is None:
            return ""
        return value

    @field_validator("patient_info", mode="before")
    @classmethod
    def _coerce_patient_info_values_to_str(cls, value):
        if value is None:
            return {}
        if isinstance(value, dict):
            coerced: dict[str, str] = {}
            for key, item in value.items():
                if item is None:
                    coerced[str(key)] = ""
                else:
                    coerced[str(key)] = str(item)
            return coerced
        return value

    @field_validator("vitals", mode="before")
    @classmethod
    def _coerce_vitals(cls, value):
        if value is None:
            return {}
        return value

    @field_validator(
        "encounter_info",
        "review_of_systems",
        "social_history",
        "assessment",
        "plan",
        "clinician_approval",
        mode="before",
    )
    @classmethod
    def _coerce_nested_models(cls, value):
        if value is None:
            return {}
        return value

    @field_validator(
        "lab_tests_ordered",
        "current_medications_mentioned",
        "return_precautions",
        "missing_but_relevant_information",
        mode="before",
    )
    @classmethod
    def _coerce_string_lists(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            cleaned = value.strip()
            return [cleaned] if cleaned else []
        if isinstance(value, list):
            return [
                str(item) for item in value if item is not None and str(item).strip()
            ]
        return value

    @field_validator("medications", mode="before")
    @classmethod
    def _coerce_medications(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            cleaned = value.strip()
            return (
                [
                    {
                        "name": cleaned,
                        "dosage": "",
                        "frequency": "",
                        "duration": "",
                    }
                ]
                if cleaned
                else []
            )
        if isinstance(value, list):
            coerced_items = []
            for item in value:
                if item is None:
                    continue
                if isinstance(item, str):
                    cleaned = item.strip()
                    if not cleaned:
                        continue
                    coerced_items.append(
                        {
                            "name": cleaned,
                            "dosage": "",
                            "frequency": "",
                            "duration": "",
                        }
                    )
                else:
                    coerced_items.append(item)
            return coerced_items
        return value


# --- Doctor edit tracking -----------------------------------------------


class DoctorEdit(BaseModel):
    field_path: str
    old_value: str
    new_value: str
    edited_at: datetime | None = None


class GeneratedDocumentStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISED = "revised"


class TranscriptDocument(BaseModel):
    file_name: str | None = None
    content_type: str = "text/plain"
    storage_backend: str = "inline"
    gridfs_file_id: str | None = None
    full_text: str = ""


class EditedClinicalNotes(BaseModel):
    patient_info: dict[str, str] = Field(default_factory=dict)
    chief_complaint: str = ""
    history_of_present_illness: str = ""
    past_medical_history: str = ""
    allergies: str = ""
    vitals: Vitals = Field(default_factory=Vitals)
    examination_findings: str = ""
    diagnosis: str = ""
    medications: list[Medication] = Field(default_factory=list)
    lab_tests_ordered: list[str] = Field(default_factory=list)
    follow_up: str = ""
    patient_instructions: str = ""
    clinical_notes_summary: str = ""


# --- MongoDB: generated_documents (Collection 3) -----------------------


class DocumentVersionEntry(BaseModel):
    """Immutable snapshot of a GeneratedDocument at a specific version."""

    version: int
    snapshot: GeneratedClinicalNotes
    edit_summary: str = ""
    created_at: datetime | None = None


class GeneratedDocument(BaseModel):
    """Staging area for LLM outputs. Doctor reviews here before approval."""

    id: str | None = None
    consultation_id: int
    doctor_id: int
    patient_id: int
    document_type: str = "clinical_notes_and_prescription"
    generated_output: GeneratedClinicalNotes = Field(
        default_factory=GeneratedClinicalNotes
    )
    normalized_transcript: NormalizedTranscript | None = None
    suggestive_output: SuggestiveReview | None = None
    report_metadata: LlmExecutionMetadata | None = None
    suggestive_metadata: LlmExecutionMetadata | None = None
    doctor_edits: list[DoctorEdit] = Field(default_factory=list)
    version: int = 1
    version_history: list[DocumentVersionEntry] = Field(default_factory=list)
    status: GeneratedDocumentStatus = GeneratedDocumentStatus.PENDING_REVIEW
    approved_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# --- MongoDB: consultation_documents (Collection 4) --------------------


class ConsultationDocument(BaseModel):
    """Stores transcript + AI notes + doctor edits per consultation."""

    id: str | None = None
    consultation_id: int
    transcript: TranscriptDocument = Field(default_factory=TranscriptDocument)
    normalized_transcript: NormalizedTranscript | None = None
    normalization_metadata: LlmExecutionMetadata | None = None
    ai_clinical_notes: GeneratedClinicalNotes | None = None
    ai_suggestions: SuggestiveReview | None = None
    doctor_edited_notes: EditedClinicalNotes | None = None
    edit_history: list[DoctorEdit] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


# --- MongoDB: llm_prompts (Collection 2) --------------------------------


class LlmPromptConfig(BaseModel):
    """Stored in MongoDB so prompts can be updated without redeploying."""

    id: str
    prompt_name: str
    version: int = 1
    model_target: str = ""
    system_prompt: str = ""
    user_prompt_template: str = ""
    temperature: float = 0.2
    max_tokens: int = 2048
    created_at: datetime | None = None
    updated_at: datetime | None = None


# --- Repository contracts -----------------------------------------------


class GeneratedDocumentRepository(ABC):
    @abstractmethod
    def get_by_consultation_id(
        self, consultation_id: int
    ) -> GeneratedDocument | None: ...

    @abstractmethod
    def save(self, document: GeneratedDocument) -> GeneratedDocument: ...

    def get_version_history(self, consultation_id: int) -> list[DocumentVersionEntry]:
        """Return the full version history for a consultation's generated document."""
        doc = self.get_by_consultation_id(consultation_id)
        return doc.version_history if doc else []


class ConsultationDocumentRepository(ABC):
    @abstractmethod
    def get_by_consultation_id(
        self, consultation_id: int
    ) -> ConsultationDocument | None: ...

    @abstractmethod
    def save(self, document: ConsultationDocument) -> ConsultationDocument: ...


class PrescriptionArtifact(BaseModel):
    id: str | None = None
    prescription_id: int
    consultation_id: int
    doctor_id: int
    patient_id: int
    version: int = 1
    artifact_type: str = "prescription_pdf"
    storage_backend: str = "gridfs"
    gridfs_file_id: str | None = None
    file_name: str
    content_type: str = "application/pdf"
    byte_size: int | None = None
    checksum_sha256: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TranscriptNormalizationRequest(BaseModel):
    consultation_id: int
    transcript_text: str
    prompt: LlmPromptConfig


class ClinicalReportRequest(BaseModel):
    consultation_id: int
    doctor_id: int
    patient_id: int

    patient_name: str = ""
    patient_age: str = ""
    patient_gender: str = ""
    patient_date_of_birth: str = ""
    patient_phone: str = ""
    patient_address: str = ""
    patient_allergies: str = ""
    patient_medical_history: str = ""

    clinician_name: str = ""
    facility_name: str = ""
    department: str = ""
    visit_type: str = ""
    consultation_mode: str = ""
    encounter_date: str = ""
    encounter_time: str = ""

    transcript_text: str
    normalized_transcript: NormalizedTranscript
    prompt: LlmPromptConfig


class LlmReportEnvelope(BaseModel):
    normalized_transcript: NormalizedTranscript
    generated_notes: GeneratedClinicalNotes


class PrescriptionArtifactRepository(ABC):
    @abstractmethod
    def get_latest_by_prescription_id(
        self, prescription_id: int
    ) -> PrescriptionArtifact | None: ...

    @abstractmethod
    def save(self, artifact: PrescriptionArtifact) -> PrescriptionArtifact: ...


class PromptRepository(ABC):
    @abstractmethod
    def list_prompts(self) -> list[LlmPromptConfig]: ...

    @abstractmethod
    def get_by_id(self, prompt_id: str) -> LlmPromptConfig | None: ...

    @abstractmethod
    def save(self, prompt: LlmPromptConfig) -> LlmPromptConfig: ...


class ClinicalNoteGenerator(ABC):
    @abstractmethod
    def generate(self, request: ClinicalReportRequest) -> GeneratedClinicalNotes:
        """Run LLM to produce clinical notes + prescription draft."""


class TranscriptNormalizer(ABC):
    @abstractmethod
    def normalize(
        self, request: TranscriptNormalizationRequest
    ) -> NormalizedTranscript:
        """Clean and reorder transcript text without inventing facts."""


class LocalLlmHealthService(ABC):
    @abstractmethod
    def check_health(self) -> LlmHealthStatus:
        """Return Ollama connectivity and configured-model readiness."""
