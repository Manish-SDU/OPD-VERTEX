"""Consultation domain models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
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
    """Maps to SQL table: consultations."""

    id: int | None = None
    doctor_id: int
    patient_id: int
    chief_complaint: str | None = None
    visit_type: str | None = None
    status: ConsultationStatus = ConsultationStatus.RECORDING
    started_at: datetime | None = None
    ended_at: datetime | None = None
    approved_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConsultationCreateRequest(BaseModel):
    patient_id: int
    chief_complaint: str | None = None
    visit_type: str | None = None


class ConsultationRepository(ABC):
    @abstractmethod
    def list_all(self) -> list[Consultation]:
        """Return consultations."""

    @abstractmethod
    def get_by_id(self, consultation_id: int) -> Consultation | None:
        """Return consultation by id."""

    @abstractmethod
    def create(self, consultation: Consultation) -> Consultation:
        """Persist a new consultation."""

    @abstractmethod
    def update_status(self, consultation_id: int, status: ConsultationStatus) -> None:
        """Update consultation workflow status."""
