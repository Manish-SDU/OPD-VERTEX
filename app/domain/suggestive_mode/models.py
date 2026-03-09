"""Suggestive review models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class Suggestion(BaseModel):
    code: str
    severity: str
    message: str


class SuggestiveReview(BaseModel):
    consultation_id: str
    suggestions: list[Suggestion]


class SuggestiveModeService(ABC):
    @abstractmethod
    def review(self, consultation_id: str, document_text: str) -> SuggestiveReview:
        """Return placeholder safety review."""
