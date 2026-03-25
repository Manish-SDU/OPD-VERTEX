"""Prescription models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime

from pydantic import BaseModel, Field


class Medication(BaseModel):
    """Single medication entry stored as JSON in prescriptions.medications."""

    name: str
    dosage: str
    frequency: str
    duration: str
    route: str = "oral"
    special_instructions: str | None = None


class Prescription(BaseModel):
    """Maps to SQL table: prescriptions."""

    id: int | None = None
    consultation_id: int
    doctor_id: int
    patient_id: int
    diagnosis: str
    medications: list[Medication] = Field(default_factory=list)
    instructions: str | None = None
    follow_up_date: date | None = None
    is_approved: bool = False
    is_emailed: bool = False
    emailed_at: datetime | None = None
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PrescriptionRepository(ABC):
    @abstractmethod
    def list_all(self) -> list[Prescription]:
        """Return prescriptions."""

    @abstractmethod
    def get_by_id(self, prescription_id: int) -> Prescription | None:
        """Return prescription by id."""

    @abstractmethod
    def create(self, prescription: Prescription) -> Prescription:
        """Persist a new approved prescription."""
