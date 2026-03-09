"""PDF generation contract."""

from __future__ import annotations

from abc import ABC, abstractmethod


class PdfGenerator(ABC):
    @abstractmethod
    def generate_prescription_pdf(self, prescription_id: int) -> str:
        """Generate a prescription PDF and return the file path."""
