"""Appointment domain models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class AppointmentStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class Appointment(BaseModel):
    """Maps to SQL table: appointments."""

    id: int | None = None
    patient_id: int
    doctor_id: int
    scheduled_at: datetime
    duration_minutes: int = 30
    status: AppointmentStatus = AppointmentStatus.PENDING
    reason: str
    notes: str | None = None
    consultation_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AppointmentCreateRequest(BaseModel):
    patient_id: int
    doctor_id: int
    scheduled_at: datetime
    duration_minutes: int = 30
    reason: str
    notes: str | None = None


class AppointmentRepository(ABC):
    @abstractmethod
    def list_all(self) -> list[Appointment]:
        """Return all appointments ordered by priority queue rules."""

    @abstractmethod
    def get_by_id(self, appointment_id: int) -> Appointment | None:
        """Return appointment by id."""

    @abstractmethod
    def list_by_patient(self, patient_id: int) -> list[Appointment]:
        """Return all appointments for a patient."""

    @abstractmethod
    def list_by_doctor(self, doctor_id: int) -> list[Appointment]:
        """Return all appointments for a doctor."""

    @abstractmethod
    def create(self, request: AppointmentCreateRequest) -> Appointment:
        """Persist a new appointment."""

    @abstractmethod
    def update_status(
        self, appointment_id: int, status: AppointmentStatus
    ) -> Appointment | None:
        """Update appointment status."""

    @abstractmethod
    def cancel(self, appointment_id: int) -> Appointment | None:
        """Cancel an appointment."""

    @abstractmethod
    def link_consultation(
        self, appointment_id: int, consultation_id: int
    ) -> Appointment | None:
        """Store the consultation_id once a consultation is started from this appointment."""
