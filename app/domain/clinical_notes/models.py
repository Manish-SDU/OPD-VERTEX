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


class NormalizedTranscript(BaseModel):
    """LLM-cleaned transcript that preserves meaning and chronology."""

    raw_text: str = ""
    normalized_text: str = ""
    chronology_notes: list[str] = Field(default_factory=list)
    removed_noise: list[str] = Field(default_factory=list)
    unresolved_segments: list[str] = Field(default_factory=list)
    language: str = "en"

    @field_validator(
        "chronology_notes",
        "removed_noise",
        "unresolved_segments",
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
            # If the model returns a single string, keep it as one note.
            # (We avoid splitting heuristics to preserve original meaning.)
            return [cleaned]
        return value


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


class GeneratedClinicalNotes(BaseModel):
    """Structure returned by the Prescription & Clinical Notes Generator prompt."""

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

    @field_validator(
        "chief_complaint",
        "history_of_present_illness",
        "past_medical_history",
        "allergies",
        "examination_findings",
        "diagnosis",
        "follow_up",
        "patient_instructions",
        "clinical_notes_summary",
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

    @field_validator("lab_tests_ordered", mode="before")
    @classmethod
    def _coerce_lab_tests_ordered(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            cleaned = value.strip()
            return [cleaned] if cleaned else []
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
