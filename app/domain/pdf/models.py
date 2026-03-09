"""PDF generation contract."""

from __future__ import annotations

from abc import ABC, abstractmethod


class PdfGenerator(ABC):
    @abstractmethod
    def generate_prescription_pdf(self, prescription_id: str) -> str:
        """Generate placeholder PDF path."""
