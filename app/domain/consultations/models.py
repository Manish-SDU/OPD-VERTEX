"""Consultation domain models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum

from pydantic import BaseModel


class ConsultationStatus(StrEnum):
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    PROCESSING = "processing"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class Consultation(BaseModel):
    id: str
    patient_id: str
    clinician_id: str
    status: ConsultationStatus
    chief_complaint: str
    transcript_document_id: str | None = None
    generated_document_id: str | None = None


class ConsultationCreateRequest(BaseModel):
    patient_id: str
    chief_complaint: str


class ConsultationRepository(ABC):
    @abstractmethod
    def list_all(self) -> list[Consultation]:
        """Return consultations."""

    @abstractmethod
    def get_by_id(self, consultation_id: str) -> Consultation | None:
        """Return consultation by id."""

    @abstractmethod
    def create(self, payload: ConsultationCreateRequest, clinician_id: str) -> Consultation:
        """Create a mock consultation."""
