"""Clinical note generation domain contracts.

Maps to MongoDB collections: generated_documents, consultation_documents, llm_prompts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.domain.prescriptions.models import Medication
from app.domain.suggestive_mode.models import SuggestiveReview


# --- Vitals sub-model --------------------------------------------------


class Vitals(BaseModel):
    blood_pressure: str = "Not recorded"
    heart_rate: str = "Not recorded"
    temperature: str = "Not recorded"
    respiratory_rate: str = "Not recorded"
    spo2: str = "Not recorded"


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
    suggestive_output: SuggestiveReview | None = None
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
    def generate(self, consultation_id: int, transcript_text: str) -> GeneratedDocument:
        """Run LLM to produce clinical notes + prescription draft."""
