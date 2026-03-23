"""MongoDB seed data.

Gabriele and Mats: run this script once to populate the llm_prompts and
email_templates collections with the initial documents from the PDF spec.

Usage: python -m app.infrastructure.db.mongo.seeds
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.infrastructure.db.mongo.connection import get_database
from app.infrastructure.db.mongo.collections.names import EMAIL_TEMPLATES, LLM_PROMPTS


def seed_llm_prompts(db) -> None:
    collection = db[LLM_PROMPTS]
    if collection.count_documents({}) > 0:
        print("llm_prompts already seeded, skipping.")
        return

    now = datetime.now(timezone.utc).isoformat()

    collection.insert_many(
        [
            {
                "_id": "prescription_generation_v1",
                "prompt_name": "Prescription & Clinical Notes Generator",
                "version": 1,
                "model_target": "llama3.1-8b OR mistral-7b-v0.3",
                "system_prompt": "TODO: paste full system prompt from PDF spec",
                "user_prompt_template": "TODO: paste full user prompt template from PDF spec",
                "temperature": 0.2,
                "max_tokens": 2048,
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": "suggestive_mode_v1",
                "prompt_name": "Suggestive Mode -- Clinical Safety Net",
                "version": 1,
                "model_target": "llama3.1-8b OR mistral-7b-v0.3",
                "system_prompt": "TODO: paste full system prompt from PDF spec",
                "user_prompt_template": "TODO: paste full user prompt template from PDF spec",
                "temperature": 0.3,
                "max_tokens": 1500,
                "created_at": now,
                "updated_at": now,
            },
        ]
    )
    print("Seeded llm_prompts (2 documents).")


def seed_email_templates(db) -> None:
    collection = db[EMAIL_TEMPLATES]
    if collection.count_documents({}) > 0:
        print("email_templates already seeded, skipping.")
        return

    now = datetime.now(timezone.utc).isoformat()

    collection.insert_one(
        {
            "_id": "prescription_delivery_v1",
            "template_name": "Prescription Delivery Email",
            "version": 1,
            "subject_template": "Your Prescription from Dr. {{doctor_name}} -- {{clinic_name}}",
            "body_template": "TODO: paste full body template from PDF spec",
            "from_email": "noreply@{{clinic_domain}}",
            "reply_to": "{{doctor_email}}",
            "attachment_fields": {
                "filename_template": "Prescription_{{patient_last_name}}_{{consultation_date}}.pdf",
                "mime_type": "application/pdf",
            },
            "placeholders": [
                "patient_first_name",
                "patient_last_name",
                "doctor_name",
                "doctor_first_name",
                "doctor_last_name",
                "doctor_specialization",
                "doctor_email",
                "clinic_name",
                "clinic_domain",
                "clinic_phone",
                "clinic_address",
                "consultation_date",
                "consultation_time",
                "diagnosis",
                "follow_up_date",
                "medications",
                "patient_instructions",
            ],
            "created_at": now,
            "updated_at": now,
        }
    )
    print("Seeded email_templates (1 document).")


if __name__ == "__main__":
    db = get_database()
    seed_llm_prompts(db)
    seed_email_templates(db)
    print("Done.")
