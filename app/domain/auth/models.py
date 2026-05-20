"""Authentication domain models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


USER_ROLES = ("patient", "doctor", "admin")


class User(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: Literal["patient", "doctor", "admin"]
    is_active: bool = True


class Staff(BaseModel):
    """Maps to SQL table: staff."""

    id: int | None = None
    first_name: str
    last_name: str
    email: str
    password_hash: str = ""
    specialization: str | None = None
    license_number: str | None = None
    phone: str | None = None
    role: Literal["doctor", "admin"]
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_user(self) -> User:
        return User(
            id=self.id or 0,
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name,
            role=self.role,
            is_active=self.is_active,
        )


class StaffCreateRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    password_hash: str
    role: str
    specialization: str | None = None
    license_number: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthService(ABC):
    from app.domain.patients.models import PatientCreateRequest, PatientRepository

    patient_repository: PatientRepository  # For cross-repository operations if needed
    staff_repository: StaffRepository

    @abstractmethod
    def authenticate(self, email: str, password: str) -> User | None:
        """Try staff first, then patient authentication."""

    @abstractmethod
    def get_current_user(self) -> User | None:
        """Return current authenticated user object."""


class StaffRepository(ABC):
    @abstractmethod
    def list_all(self) -> list[Staff]:
        """Return all staff members."""

    @abstractmethod
    def get_by_email(self, email: str) -> Staff | None:
        """Fetch staff by email."""

    @abstractmethod
    def get_by_id(self, staff_id: int) -> Staff | None:
        """Fetch staff by id."""

    @abstractmethod
    def create(self, staff: StaffCreateRequest) -> Staff:
        """Persist a new staff."""
