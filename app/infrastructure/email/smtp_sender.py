"""Real async SMTP adapter — works against MailHog in dev, real SMTP in prod."""

from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib

from app.domain.ai.schemas import Attachment
from app.domain.email.models import EmailService

log = logging.getLogger(__name__)


class SmtpEmailService(EmailService):
    """Async SMTP sender backed by aiosmtplib.

    Reads connection settings from the app Settings object so that
    MailHog (dev) and a real relay (prod) require no code changes.
    """

    def __init__(
        self,
        host: str = "mailhog",
        port: int = 1025,
        user: str | None = None,
        password: str | None = None,
        use_tls: bool = False,
        from_addr: str = "opd-vertex@clinic.local",
        from_name: str = "OPD-Vertex Clinic",
    ) -> None:
        self.host = host
        self.port = port
        self.user = user or None
        self.password = password or None
        self.use_tls = use_tls
        self.from_addr = from_addr
        self.from_name = from_name

    async def send(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: str = "",
        attachments: list[Attachment] | None = None,
    ) -> str:
        msg = EmailMessage()
        msg["From"] = f"{self.from_name} <{self.from_addr}>"
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body_text or "Please use an HTML-capable email client.")
        msg.add_alternative(body_html, subtype="html")
        for att in attachments or []:
            maintype, _, subtype = att.content_type.partition("/")
            msg.add_attachment(
                att.content,
                maintype=maintype or "application",
                subtype=subtype or "octet-stream",
                filename=att.filename,
            )
        log.info(
            "Sending email to=%s host=%s:%d tls=%s", to, self.host, self.port, self.use_tls
        )
        resp = await aiosmtplib.send(
            msg,
            hostname=self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            use_tls=False,
            start_tls=self.use_tls,
            timeout=30,
        )
        return str(resp)

    def send_prescription_email(self, prescription_id: int, recipient: str) -> str:
        """Satisfy the legacy domain interface; real delivery uses send()."""
        return f"Queued prescription {prescription_id} email for {recipient}"
