"""
Pydantic schemas used by the AI pipeline (LLM in/out, transcript, suggestions).
These are the contracts the components agree on.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    is_partial: bool = False
    hallucination_flags: list[str] = Field(default_factory=list)


class FinalTranscript(BaseModel):
    segments: list[TranscriptSegment] = Field(default_factory=list)
    full_text: str = ""
    confidence_avg: float | None = None
    hallucination_rate: float = 0.0
    language: str | None = None
    duration_s: float | None = None


class PrescriptionItem(BaseModel):
    drug: str
    dose: str = ""
    frequency: str = ""
    duration: str = ""
    route: str = ""
    notes: str = ""


class Prescription(BaseModel):
    items: list[PrescriptionItem] = Field(default_factory=list)
    advice: str = ""
    follow_up: str = ""


class SOAPNote(BaseModel):
    subjective: str
    objective: str
    assessment: str
    plan: str
    prescription: Prescription = Field(default_factory=Prescription)


class Suggestion(BaseModel):
    type: Literal["investigation", "medication_check", "referral", "lifestyle", "safety", "other"] = "other"
    severity: Literal["low", "medium", "high"] = "low"
    message: str
    source: Literal["rule", "llm"]
    rule_id: str | None = None


class SuggesterOutput(BaseModel):
    items: list[Suggestion] = Field(default_factory=list)


class PatientContext(BaseModel):
    """Minimal patient info passed to the LLM."""
    full_name: str
    dob: date | None = None
    sex: str | None = None
    allergies_text: str = ""
    chronic_conditions_text: str = ""


class DoctorContext(BaseModel):
    full_name: str
    specialty: str | None = None
    license_no: str | None = None


class Attachment(BaseModel):
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


class ConsultationBundle(BaseModel):
    """The full package generated for a consultation."""
    consultation_id: int
    transcript: FinalTranscript
    note: SOAPNote
    suggestions: SuggesterOutput
    generated_at: datetime
