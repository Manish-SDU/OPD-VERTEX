"""Prompt assembly for the SOAP note summarizer and clinical suggester."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.domain.ai.schemas import PatientContext, SOAPNote

_PROMPT_DIR = Path(__file__).parent.parent.parent / "infrastructure" / "prompts"


@lru_cache
def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _summarizer_path() -> Path:
    return _PROMPT_DIR / "summarizer_system.md"


def _suggester_path() -> Path:
    return _PROMPT_DIR / "suggester_system.md"


def build_summarizer_messages(
    *, transcript_text: str, patient: PatientContext, appointment_at: str
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the SOAP note generator."""
    system = _read(_summarizer_path())
    schema_json = SOAPNote.model_json_schema()
    user = (
        f"=== Patient ===\n"
        f"Name: {patient.full_name}\n"
        f"DOB: {patient.dob}\n"
        f"Sex: {patient.sex}\n"
        f"Known Allergies: {patient.allergies_text or 'none reported'}\n"
        f"Chronic Conditions: {patient.chronic_conditions_text or 'none reported'}\n"
        f"Appointment: {appointment_at}\n\n"
        f"=== Transcript ===\n"
        f"{transcript_text}\n\n"
        f"=== Output schema (return JSON conforming exactly to this) ===\n"
        f"{schema_json}\n"
    )
    return system, user


def build_suggester_user(
    *, transcript_text: str, note: SOAPNote, fired_rules_summary: str
) -> str:
    """Return the user prompt for the LLM suggester pass."""
    return (
        f"Transcript:\n{transcript_text}\n\n"
        f"Doctor SOAP:\n{note.model_dump_json(indent=2)}\n\n"
        f"Rules already fired (do not duplicate):\n{fired_rules_summary or '(none)'}"
    )
