"""Suggestive review models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
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


class SuggestiveModeService(ABC):
    @abstractmethod
    def review(self, consultation_id: int, document_json: str) -> SuggestiveReview:
        """Review generated notes and flag clinical concerns."""
