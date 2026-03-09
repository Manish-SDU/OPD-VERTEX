"""Authentication domain models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class Staff(BaseModel):
    id: str
    username: str
    full_name: str
    role: str


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthService(ABC):
    @abstractmethod
    def authenticate(self, username: str, password: str) -> Staff | None:
        """Authenticate a user. Replace with real auth later."""

    @abstractmethod
    def get_current_staff(self) -> Staff:
        """Return current placeholder staff object."""


class StaffRepository(ABC):
    @abstractmethod
    def get_by_username(self, username: str) -> Staff | None:
        """Fetch staff by username."""
