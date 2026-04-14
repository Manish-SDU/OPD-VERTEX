"""Suggestive review models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SuggestionType(StrEnum):
    OMISSION = "OMISSION"
    CONTRAINDICATION = "CONTRAINDICATION"
    DOSAGE_CHECK = "DOSAGE_CHECK"
    STANDARD_OF_CARE = "STANDARD_OF_CARE"
    INTERACTION_WARNING = "INTERACTION_WARNING"
    FOLLOW_UP = "FOLLOW_UP"


class SuggestionSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskLevel(StrEnum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class Suggestion(BaseModel):
    type: SuggestionType
    severity: SuggestionSeverity
    title: str
    detail: str
    recommendation: str
    source_quote: str = "N/A"


class SuggestiveReview(BaseModel):
    consultation_id: int
    suggestions: list[Suggestion] = Field(default_factory=list)
    overall_risk_level: RiskLevel = RiskLevel.GREEN
    summary: str = ""


class SuggestiveReviewRequest(BaseModel):
    consultation_id: int
    doctor_id: int
    patient_id: int
    generated_report: dict[str, object]
    normalized_transcript: dict[str, object] | None = None
    system_prompt: str
    user_prompt_template: str
    temperature: float = 0.2
    max_tokens: int = 1500
    requested_at: datetime | None = None


class SuggestiveModeService(ABC):
    @abstractmethod
    def review(self, request: SuggestiveReviewRequest) -> SuggestiveReview:
        """Review generated notes and flag clinical concerns."""
