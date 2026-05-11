"""PDF generation contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.clinical_notes.models import PrescriptionArtifact
from app.domain.prescriptions.models import Prescription

from datetime import datetime
from pydantic import BaseModel


class ConsultationMetadata(BaseModel):
    """Metadata for rendering in pdf header"""

    consultation_id: int
    patient_name: str
    patient_dob: str | None = None
    clinician_name: str
    consultation_date: datetime
    visit_type: str | None = None


class ReportPdfArtifact(BaseModel):
    """Pdf file metadata after generation"""

    file_path: str
    file_name: str
    file_size_kb: float
    generated_at: datetime


class PrescriptionData(BaseModel):
    """Structured prescription for PDF rendering"""

    prescription_id: int
    patient_name: str
    mediications: list[dict]
    prescribed_date: datetime


class PdfGenerator(ABC):
    @abstractmethod
    def generate_report_pdf(
        self, report_markdown: str, consultation_metadata: ConsultationMetadata
    ) -> str:
        "Generate pdf report"

    @abstractmethod
    def generate_prescription_pdf(
        self, prescription: Prescription
    ) -> PrescriptionArtifact:
        """Generate prescription PDF metadata without leaking SQL storage details."""
