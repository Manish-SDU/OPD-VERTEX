"""Patient domain models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class Patient(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    date_of_birth: str | None = None
    notes: str | None = None


class PatientCreateRequest(BaseModel):
    first_name: str
    last_name: str
    email: str | None = None


class PatientRepository(ABC):
    @abstractmethod
    def list_all(self) -> list[Patient]:
        """Return all patients."""

    @abstractmethod
    def get_by_id(self, patient_id: str) -> Patient | None:
        """Return patient by id."""

    @abstractmethod
    def create(self, payload: PatientCreateRequest) -> Patient:
        """Create a mock patient."""
