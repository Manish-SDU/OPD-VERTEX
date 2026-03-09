"""Placeholder ReportLab adapter."""

from __future__ import annotations

from app.domain.pdf.models import PdfGenerator


class ReportLabPdfGenerator(PdfGenerator):
    def generate_prescription_pdf(self, prescription_id: str) -> str:
        # TODO: render a real PDF to the configured output directory with ReportLab.
        return f"/tmp/{prescription_id}.pdf"
