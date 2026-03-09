"""Email domain models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class EmailTemplate(BaseModel):
    id: str
    name: str
    subject: str
    body: str


class EmailTemplateRepository(ABC):
    @abstractmethod
    def list_templates(self) -> list[EmailTemplate]:
        """Return mock email templates."""


class EmailService(ABC):
    @abstractmethod
    def send_prescription_email(self, prescription_id: str, recipient: str) -> str:
        """Send placeholder email and return a status message."""
