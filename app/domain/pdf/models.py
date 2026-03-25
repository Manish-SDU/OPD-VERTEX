"""PDF generation contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.clinical_notes.models import PrescriptionArtifact
from app.domain.prescriptions.models import Prescription


class PdfGenerator(ABC):
    @abstractmethod
    def generate_prescription_pdf(
        self, prescription: Prescription
    ) -> PrescriptionArtifact:
        """Generate prescription PDF metadata without leaking SQL storage details."""
