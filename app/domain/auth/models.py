"""Authentication domain models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, Field


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
    role: str = "doctor"
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthService(ABC):
    @abstractmethod
    def authenticate(self, email: str, password: str) -> Staff | None:
        """Authenticate a user by email + password."""

    @abstractmethod
    def get_current_staff(self) -> Staff:
        """Return current staff object."""


class StaffRepository(ABC):
    @abstractmethod
    def get_by_email(self, email: str) -> Staff | None:
        """Fetch staff by email."""

    @abstractmethod
    def get_by_id(self, staff_id: int) -> Staff | None:
        """Fetch staff by id."""
