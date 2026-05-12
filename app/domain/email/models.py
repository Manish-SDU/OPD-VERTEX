"""Email domain models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, Field


class EmailTemplate(BaseModel):
    """Maps to MongoDB collection: email_templates."""

    id: str
    template_name: str
    version: int = 1
    subject_template: str
    body_template: str
    placeholders: list[str] = Field(default_factory=list)
    from_email: str = ""
    reply_to: str = ""
    attachment_fields: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EmailTemplateRepository(ABC):
    @abstractmethod
    def list_templates(self) -> list["EmailTemplate"]:
        """Return email templates."""

    @abstractmethod
    def get_by_id(self, template_id: str) -> "EmailTemplate | None":
        """Return a single email template."""

    @abstractmethod
    def save(self, template: "EmailTemplate") -> "EmailTemplate":
        """Persist an email template."""


class EmailAttachment(BaseModel):
    filename: str
    content_type: str
    data: bytes


class EmailMessage(BaseModel):
    to_email: str
    to_name: str | None = None
    subject: str
    text_body: str
    html_body: str | None = None
    attachment: EmailAttachment | None = None


class EmailService(ABC):
    @abstractmethod
    def send_email(self, message: EmailMessage) -> dict:
        """Send an email and return provider/result metadata."""
