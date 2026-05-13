"""Startup email template bootstrap for MongoDB."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from logging import getLogger
from typing import Any

from pymongo.database import Database

from app.infrastructure.db.mongo.collections.names import EMAIL_TEMPLATES

logger = getLogger("opd_vertex.infrastructure.bootstrap.email_templates")


EMAIL_TEMPLATE_DOCUMENTS: tuple[dict[str, Any], ...] = (
    {
        "_id": "prescription_delivery_v1",
        "template_name": "Prescription Delivery Email",
        "version": 1,
        "subject_template": "Your Prescription from Dr. {{doctor_name}}",
        "body_template": (
            "Hello {{patient_name}},\n\n"
            "Your prescription from Dr. {{doctor_name}} is attached.\n\n"
            "Regards,\nOPD-Vertex"
        ),
        "placeholders": ["patient_name", "doctor_name"],
        "from_email": "",
        "reply_to": "",
        "attachment_fields": {"prescription_pdf": "required"},
    },
)


@dataclass(slots=True)
class EmailTemplateSeedResult:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0


class EmailTemplateBootstrapSeeder:
    def __init__(self, db: Database) -> None:
        self.collection = db[EMAIL_TEMPLATES]

    def seed(self) -> EmailTemplateSeedResult:
        result = EmailTemplateSeedResult()
        now = datetime.now(timezone.utc)

        for template in EMAIL_TEMPLATE_DOCUMENTS:
            template_id = template["_id"]
            existing = self.collection.find_one({"_id": template_id})

            if existing is None:
                self.collection.insert_one(
                    {**template, "created_at": now, "updated_at": now}
                )
                result.inserted += 1
                logger.info("Email template seed inserted: %s", template_id)
                continue

            comparable_existing = {
                key: value
                for key, value in existing.items()
                if key not in {"created_at", "updated_at"}
            }
            if comparable_existing == dict(template):
                result.skipped += 1
                logger.info("Email template seed skipped: %s", template_id)
                continue

            self.collection.replace_one(
                {"_id": template_id},
                {
                    **template,
                    "created_at": existing.get("created_at", now),
                    "updated_at": now,
                },
                upsert=True,
            )
            result.updated += 1
            logger.info("Email template seed updated: %s", template_id)

        logger.info(
            "Email template bootstrap complete. inserted=%s updated=%s skipped=%s",
            result.inserted,
            result.updated,
            result.skipped,
        )
        return result
