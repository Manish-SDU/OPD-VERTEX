from __future__ import annotations

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.domain.email.models import EmailMessage, EmailService


class SmtpEmailService(EmailService):
    def __init__(
        self,
        host: str,
        port: int,
        from_email: str,
        from_name: str,
        username: str = "",
        password: str = "",
    ) -> None:
        self.host = host
        self.port = port
        self.from_email = from_email
        self.from_name = from_name
        self.username = username
        self.password = password

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
            subtype = "pdf"
            if (
                message.attachment.content_type
                and "/" in message.attachment.content_type
            ):
                _, subtype = message.attachment.content_type.split("/", 1)

            part = MIMEApplication(
                message.attachment.data,
                _subtype=subtype,
                Name=message.attachment.filename,
            )
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=message.attachment.filename,
            )
            msg.attach(part)

        # Port 465 → implicit SSL; port 587 → STARTTLS; everything else → plain
        if self.port == 465:
            with smtplib.SMTP_SSL(self.host, self.port) as server:
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)
        elif self.port == 587:
            with smtplib.SMTP(self.host, self.port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)
        else:
            # Plain SMTP – used for MailHog (port 1025) in dev
            with smtplib.SMTP(self.host, self.port) as server:
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)

        provider = (
            "smtp-ssl"
            if self.port == 465
            else ("smtp-tls" if self.port == 587 else "smtp-dev")
        )
        return {
            "status": "sent",
            "provider": provider,
            "host": self.host,
            "port": self.port,
            "recipient": str(message.to_email),
            "subject": message.subject,
        }
