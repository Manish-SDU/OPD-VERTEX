"""Placeholder SMTP adapter."""

from __future__ import annotations

from app.domain.email.models import EmailService


class SmtpEmailService(EmailService):
    def send_prescription_email(self, prescription_id: str, recipient: str) -> str:
        # TODO: implement SMTP delivery with templating and audit hooks.
        return f"TODO: send prescription {prescription_id} to {recipient}"
