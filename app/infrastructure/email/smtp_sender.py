from __future__ import annotations

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.domain.email.models import EmailMessage, EmailService


class SmtpEmailService(EmailService):
    def __init__(self, host: str, port: int, from_email: str, from_name: str) -> None:
        self.host = host
        self.port = port
        self.from_email = from_email
        self.from_name = from_name

    def send_email(self, message: EmailMessage) -> dict:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = message.subject
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = str(message.to_email)

        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(message.text_body or "", "plain", "utf-8"))

        if message.html_body:
            alt.attach(MIMEText(message.html_body, "html", "utf-8"))

        msg.attach(alt)

        if message.attachment:
            part = MIMEApplication(
                message.attachment.data,
                Name=message.attachment.filename,
            )
            part["Content-Disposition"] = (
                f'attachment; filename="{message.attachment.filename}"'
            )
            msg.attach(part)

        with smtplib.SMTP(self.host, self.port) as server:
            server.send_message(msg)

        return {
            "status": "sent",
            "provider": "smtp-dev",
            "host": self.host,
            "port": self.port,
            "recipient": str(message.to_email),
            "subject": message.subject,
        }
