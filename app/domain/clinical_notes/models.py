"""Clinical note generation domain contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class Medication(BaseModel):
    name: str
    dosage: str
    instructions: str


class GeneratedClinicalNotes(BaseModel):
    subjective: str
    objective: str
    assessment: str
    plan: str
    medications: list[Medication] = Field(default_factory=list)


class GeneratedDocument(BaseModel):
    id: str
    consultation_id: str
    notes: GeneratedClinicalNotes
    prescription_draft: list[Medication] = Field(default_factory=list)


class LlmPromptConfig(BaseModel):
    id: str
    name: str
    description: str
    template: str


class GeneratedDocumentRepository(ABC):
    @abstractmethod
    def get_by_consultation_id(self, consultation_id: str) -> GeneratedDocument | None:
        """Return generated document."""

    @abstractmethod
    def save(self, document: GeneratedDocument) -> GeneratedDocument:
        """Persist generated document."""


class PromptRepository(ABC):
    @abstractmethod
    def list_prompts(self) -> list[LlmPromptConfig]:
        """Return prompt configs."""


class ClinicalNoteGenerator(ABC):
    @abstractmethod
    def generate(self, consultation_id: str, transcript_text: str) -> GeneratedDocument:
        """Generate placeholder note and prescription draft."""
