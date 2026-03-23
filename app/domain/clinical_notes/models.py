"""Clinical note generation domain contracts.

Maps to MongoDB collections: generated_documents, consultation_documents, llm_prompts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.prescriptions.models import Medication


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
    suggestive_output: dict[str, Any] | None = None
    doctor_edits: list[DoctorEdit] = Field(default_factory=list)
    status: str = "pending_review"  # pending_review | approved | rejected | revised
    approved_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# --- MongoDB: consultation_documents (Collection 4) --------------------


class ConsultationDocument(BaseModel):
    """Stores transcript + AI notes + doctor edits per consultation."""

    id: str | None = None
    consultation_id: int
    transcript: dict[str, str] = Field(default_factory=dict)  # file_path, full_text
    ai_clinical_notes: dict[str, Any] | None = None
    ai_suggestions: dict[str, Any] | None = None
    doctor_edited_notes: dict[str, Any] | None = None
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


class PromptRepository(ABC):
    @abstractmethod
    def list_prompts(self) -> list[LlmPromptConfig]: ...

    @abstractmethod
    def get_by_id(self, prompt_id: str) -> LlmPromptConfig | None: ...


class ClinicalNoteGenerator(ABC):
    @abstractmethod
    def generate(self, consultation_id: int, transcript_text: str) -> GeneratedDocument:
        """Run LLM to produce clinical notes + prescription draft."""
