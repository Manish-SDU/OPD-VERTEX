"""Patient domain models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime

from pydantic import BaseModel


class Patient(BaseModel):
    """Maps to SQL table: patients."""

    id: int | None = None
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str | None = None  # M, F, Other
    email: str
    phone: str | None = None
    address: str | None = None
    emergency_contact: str | None = None
    blood_type: str | None = None
    allergies: str | None = None
    medical_history: str | None = None
    insurance_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PatientCreateRequest(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    email: str
    gender: str | None = None
    phone: str | None = None
    allergies: str | None = None
    medical_history: str | None = None


class PatientRepository(ABC):
    @abstractmethod
    def list_all(self) -> list[Patient]:
        """Return all patients."""

    @abstractmethod
    def get_by_id(self, patient_id: int) -> Patient | None:
        """Return patient by id."""

    @abstractmethod
    def create(self, payload: PatientCreateRequest) -> Patient:
        """Persist a new patient."""
