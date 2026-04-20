"""Startup prompt bootstrap for MongoDB."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from logging import getLogger
from typing import Any

from pymongo.database import Database

from app.infrastructure.db.mongo.collections.names import LLM_PROMPTS

logger = getLogger("opd_vertex.infrastructure.bootstrap.prompts")


PROMPT_DOCUMENTS: tuple[dict[str, Any], ...] = (
    {
        "_id": "transcript_normalization_v1",
        "prompt_name": "Transcript Normalization",
        "version": 1,
        "model_target": "qwen3:8b",
        "system_prompt": (
            "You normalize noisy ASR transcripts into a clean English clinical transcript. "
            "Return JSON only. Do not invent facts. Preserve medically relevant details. "
            "Ignore obvious ASR noise only when the intended meaning is clear."
        ),
        "user_prompt_template": (
            "Consultation {consultation_id} raw transcript: {transcript_text}\n"
            "Return a JSON object with keys raw_text, normalized_text, chronology_notes, "
            "removed_noise, unresolved_segments, language."
        ),
        "temperature": 0.1,
        "max_tokens": 1400,
    },
    {
        "_id": "clinical_report_generation_v2",
        "prompt_name": "Clinical Report Generation",
        "version": 2,
        "model_target": "qwen3:8b",
        "system_prompt": (
            "You generate a structured English medical report from a cleaned transcript. "
            "Return JSON only. Do not invent clinical facts. If data is missing, state that "
            "explicitly using English placeholders such as 'Not specified'."
        ),
        "user_prompt_template": (
            "Consultation {consultation_id}\n"
            "Raw transcript: {transcript_text}\n"
            "Normalized transcript JSON: {normalized_transcript}\n"
            "Return a JSON object with keys patient_info, chief_complaint, "
            "history_of_present_illness, past_medical_history, allergies, vitals, "
            "examination_findings, diagnosis, medications, lab_tests_ordered, "
            "follow_up, patient_instructions, clinical_notes_summary."
        ),
        "temperature": 0.2,
        "max_tokens": 2200,
    },
    {
        "_id": "clinical_report_generation_v3",
        "prompt_name": "Clinical Report Generation (Template Output)",
        "version": 3,
        "model_target": "qwen3:8b",
        "system_prompt": (
            "You generate an English outpatient clinical report from a cleaned transcript. "
            "Return JSON only. Do not invent clinical facts. If data is missing, use 'Not mentioned' "
            "for strings and [] for lists. Keep medication details exactly as stated."
        ),
        "user_prompt_template": (
            "Consultation {consultation_id}\n"
            "Facility: {facility_name} | Department: {department}\n"
            "Encounter date: {encounter_date} | time: {encounter_time}\n"
            "Clinician: {clinician_name}\n\n"
            "PATIENT METADATA\n"
            "- Name: {patient_name}\n"
            "- Age: {patient_age}\n"
            "- Gender: {patient_gender}\n"
            "- DOB: {patient_date_of_birth}\n"
            "- Phone: {patient_phone}\n"
            "- Address: {patient_address}\n"
            "- Known Allergies: {patient_allergies}\n"
            "- Medical History: {patient_medical_history}\n\n"
            "RAW TRANSCRIPT (verbatim)\n"
            "{transcript_text}\n\n"
            "NORMALIZED TRANSCRIPT JSON\n"
            "{normalized_transcript}\n\n"
            "OUTPUT\n"
            "Return exactly one valid JSON object with these keys (no extra text):\n"
            "{\n"
            '  "patient_info": {"name": "", "age": "", "gender": "", "date_of_birth": "", "patient_id": "", "phone": "", "address": ""},\n'
            '  "encounter_info": {"encounter_id": "", "date": "", "time": "", "visit_type": "", "clinician_name": "", "consultation_mode": "", "accompanied_by": "", "primary_language": "", "information_reliability": ""},\n'
            '  "chief_complaint": "",\n'
            '  "history_of_present_illness": "",\n'
            '  "review_of_systems": {"general": "", "respiratory": "", "cardiovascular": "", "gastrointestinal": "", "neurological": "", "genitourinary": "", "musculoskeletal": "", "other": ""},\n'
            '  "past_medical_history": "",\n'
            '  "current_medications_mentioned": [],\n'
            '  "allergies": "",\n'
            '  "family_history": "",\n'
            '  "social_history": {"smoking": "", "alcohol": "", "substance_use": "", "occupation": ""},\n'
            '  "vitals": {"blood_pressure": "", "heart_rate": "", "temperature": "", "respiratory_rate": "", "spo2": "", "weight": "", "height": "", "bmi": ""},\n'
            '  "examination_findings": "",\n'
            '  "assessment": {"primary_diagnosis": "", "differential_diagnoses": [], "clinical_impression": ""},\n'
            '  "diagnosis": "",\n'
            '  "medications": [{"name": "", "dosage": "", "frequency": "", "duration": "", "route": "", "special_instructions": ""}],\n'
            '  "plan": {"medications": [], "lab_tests_ordered": [], "imaging_ordered": [], "referrals": [], "follow_up": "", "patient_instructions": ""},\n'
            '  "lab_tests_ordered": [],\n'
            '  "follow_up": "",\n'
            '  "patient_instructions": "",\n'
            '  "return_precautions": [],\n'
            '  "clinical_notes_summary": "",\n'
            '  "missing_but_relevant_information": [],\n'
            '  "clinician_approval": {"status": "", "reviewed_by": "", "reviewed_at": ""},\n'
            '  "report_markdown": ""\n'
            "}\n"
            "Set report_markdown to an empty string. The system will render the final report."
        ),
        "temperature": 0.2,
        "max_tokens": 2600,
    },
    {
        "_id": "suggestive_mode_v2",
        "prompt_name": "Suggestive Mode -- Clinical Safety Net",
        "version": 2,
        "model_target": "qwen3:8b",
        "system_prompt": (
            "You are a second-pass clinical safety reviewer. Return JSON only. "
            "Flag only risks supported by the provided report or transcript context. "
            "Do not invent data. Keep all output in English."
        ),
        "user_prompt_template": (
            "Consultation {consultation_id}\n"
            "Generated report JSON: {generated_report}\n"
            "Normalized transcript JSON: {normalized_transcript}\n"
            "Return a JSON object with keys consultation_id, suggestions, overall_risk_level, "
            "summary. Each suggestion must contain keys type, severity, title, detail, "
            "recommendation, source_quote."
        ),
        "temperature": 0.3,
        "max_tokens": 1500,
    },
    {
        "_id": "suggestive_mode_v3",
        "prompt_name": "Suggestive Mode -- Clinical Safety Net v3",
        "version": 3,
        "model_target": "qwen3:8b",
        "system_prompt": (
            "You are a second-pass outpatient clinical documentation safety reviewer. "
            "Compare the generated clinical report and the normalized transcript. "
            "Return only strict JSON. Use only evidence from the report or transcript. "
            "Do not invent medical facts."
        ),
        "user_prompt_template": (
            "Consultation {consultation_id}\n"
            "Generated report JSON: {generated_report}\n"
            "Normalized transcript JSON: {normalized_transcript}\n"
            "Return a JSON object with keys consultation_id, suggestions, overall_risk_level, "
            "summary. Each suggestion must contain keys type, severity, title, detail, "
            "recommendation, source_quote."
        ),
        "temperature": 0.3,
        "max_tokens": 1500,
    },
)


@dataclass(slots=True)
class PromptSeedResult:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0


class PromptBootstrapSeeder:
    def __init__(self, db: Database) -> None:
        self.collection = db[LLM_PROMPTS]

    def seed(self) -> PromptSeedResult:
        result = PromptSeedResult()
        now = datetime.now(timezone.utc)

        for prompt in PROMPT_DOCUMENTS:
            prompt_id = prompt["_id"]
            existing = self.collection.find_one({"_id": prompt_id})

            if existing is None:
                document = {**prompt, "created_at": now, "updated_at": now}
                self.collection.insert_one(document)
                result.inserted += 1
                logger.info("Prompt seed inserted: %s", prompt_id)
                continue

            comparable_existing = {
                key: value
                for key, value in existing.items()
                if key not in {"created_at", "updated_at"}
            }
            comparable_target = dict(prompt)
            if comparable_existing == comparable_target:
                result.skipped += 1
                logger.info("Prompt seed skipped (no changes): %s", prompt_id)
                continue

            updated_document = {
                **prompt,
                "created_at": existing.get("created_at", now),
                "updated_at": now,
            }
            self.collection.replace_one(
                {"_id": prompt_id}, updated_document, upsert=True
            )
            result.updated += 1
            logger.info("Prompt seed updated: %s", prompt_id)

        logger.info(
            "Prompt bootstrap complete. inserted=%s updated=%s skipped=%s",
            result.inserted,
            result.updated,
            result.skipped,
        )
        return result
