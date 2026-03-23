"""Patient domain models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Literal

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
    password_hash: str = ""  # For patient authentication
    role: Literal["patient"] = "patient"  # Role for authentication
    is_active: bool = True  # For authentication
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_user(self) -> Patient:
        return Patient(
            id=self.id or 0,
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name,
            role=self.role,
            is_active=self.is_active,
            date_of_birth=self.date_of_birth,
        )


class PatientCreateRequest(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    email: str
    gender: str | None = None
    phone: str | None = None
    allergies: str | None = None
    medical_history: str | None = None
    password_hash: str
    role: Literal["patient"] = "patient"


class PatientRepository(ABC):
    @abstractmethod
    def list_all(self) -> list[Patient]:
        """Return all patients."""

    @abstractmethod
    def get_by_id(self, patient_id: int) -> Patient | None:
        """Return patient by id."""

    @abstractmethod
    def get_by_email(self, email: str) -> Patient | None:
        """Return patient by email."""

    @abstractmethod
    def create(self, payload: PatientCreateRequest) -> Patient:
        """Persist a new patient."""
