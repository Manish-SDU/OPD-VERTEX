"""Prescription models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.domain.clinical_notes.models import Medication


class Prescription(BaseModel):
    id: str
    consultation_id: str
    patient_id: str
    version: int
    medications: list[Medication]
    status: str


class PrescriptionRepository(ABC):
    @abstractmethod
    def list_all(self) -> list[Prescription]:
        """Return prescriptions."""

    @abstractmethod
    def get_by_id(self, prescription_id: str) -> Prescription | None:
        """Return prescription by id."""
