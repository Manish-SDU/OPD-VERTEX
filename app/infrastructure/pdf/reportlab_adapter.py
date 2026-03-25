"""Placeholder ReportLab adapter."""

from __future__ import annotations

from app.domain.clinical_notes.models import PrescriptionArtifact
from app.domain.pdf.models import PdfGenerator
from app.domain.prescriptions.models import Prescription


class ReportLabPdfGenerator(PdfGenerator):
    def generate_prescription_pdf(
        self, prescription: Prescription
    ) -> PrescriptionArtifact:
        # TODO: render a real PDF and persist the artifact via Mongo-backed storage.
        return PrescriptionArtifact(
            prescription_id=prescription.id or 0,
            consultation_id=prescription.consultation_id,
            doctor_id=prescription.doctor_id,
            patient_id=prescription.patient_id,
            version=prescription.version,
            storage_backend="mongo_metadata",
            file_name=f"prescription_{prescription.id or 'draft'}.pdf",
            byte_size=0,
        )
