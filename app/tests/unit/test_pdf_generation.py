"""Unit tests for PDF generation – ReportLab adapter and application service."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pytest

from app.domain.pdf.models import ConsultationMetadata, PdfGenerator, ReportPdfArtifact
from app.domain.prescriptions.models import Medication, Prescription
from app.infrastructure.pdf.reportlab_adapter import ReportLabPdfGenerator
from app.infrastructure.persistence.in_memory.repositories import MockPdfGenerator


# ── MockPdfGenerator unit tests ─────────────────────────────────────────────


class TestMockPdfGenerator:
    def test_generate_report_pdf_returns_path(self):
        gen = MockPdfGenerator()
        meta = ConsultationMetadata(
            consultation_id=1,
            patient_name="Alice Smith",
            clinician_name="Dr. Jones",
            consultation_date=datetime(2026, 1, 1),
        )
        path = gen.generate_report_pdf("# Report", meta)
        assert "report_smith_20260101_1" in path

    def test_generate_prescription_pdf_returns_artifact(self):
        gen = MockPdfGenerator()
        rx = Prescription(
            id=7, consultation_id=1, doctor_id=2, patient_id=3, diagnosis="Flu"
        )
        artifact = gen.generate_prescription_pdf(rx)
        assert artifact.prescription_id == 7
        assert artifact.file_name.endswith(".pdf")

    def test_is_pdf_generator_subclass(self):
        assert issubclass(MockPdfGenerator, PdfGenerator)


# ── ReportLabPdfGenerator unit tests ────────────────────────────────────────


class TestReportLabPdfGeneratorInit:
    def test_instantiation_does_not_raise(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PDF_OUTPUT_DIR", str(tmp_path))
        from app.core.config import get_settings

        get_settings.cache_clear()
        # Should not raise even when stylesheet already has BodyText
        gen = ReportLabPdfGenerator()
        assert gen is not None
        get_settings.cache_clear()

    def test_output_dir_created(self, tmp_path, monkeypatch):
        out_dir = tmp_path / "pdfs"
        monkeypatch.setenv("PDF_OUTPUT_DIR", str(out_dir))
        from app.core.config import get_settings

        get_settings.cache_clear()
        ReportLabPdfGenerator()
        assert out_dir.exists()
        get_settings.cache_clear()


class TestReportLabPdfGeneratorGenerateReport:
    @pytest.fixture
    def generator(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PDF_OUTPUT_DIR", str(tmp_path))
        from app.core.config import get_settings

        get_settings.cache_clear()
        gen = ReportLabPdfGenerator()
        get_settings.cache_clear()
        return gen

    @pytest.fixture
    def metadata(self):
        return ConsultationMetadata(
            consultation_id=42,
            patient_name="Bob Patient",
            patient_dob="1980-06-15",
            clinician_name="Dr. Ada",
            consultation_date=datetime(2026, 5, 1, 10, 0),
            visit_type="Outpatient",
        )

    def test_generates_pdf_file(self, generator, metadata):
        path = generator.generate_report_pdf(
            "# Clinical Report\n\nPatient is well.", metadata
        )
        assert Path(path).exists()
        assert path.endswith(".pdf")

    def test_raises_on_empty_markdown(self, generator, metadata):
        with pytest.raises(ValueError, match="empty"):
            generator.generate_report_pdf("", metadata)

    def test_raises_on_whitespace_only_markdown(self, generator, metadata):
        with pytest.raises(ValueError, match="empty"):
            generator.generate_report_pdf("   \n\t", metadata)

    def test_pdf_file_is_nonzero(self, generator, metadata):
        path = generator.generate_report_pdf("# Report\n\nDetails here.", metadata)
        assert Path(path).stat().st_size > 0

    def test_filename_contains_consultation_id(self, generator, metadata):
        path = generator.generate_report_pdf("# Report", metadata)
        assert "42" in Path(path).name

    def test_multiple_calls_each_produce_a_pdf(self, generator, metadata):
        """Each generate call produces a valid PDF file on disk."""
        path1 = generator.generate_report_pdf("# Report 1", metadata)
        path2 = generator.generate_report_pdf("# Report 2", metadata)
        assert os.path.exists(path1)
        assert os.path.exists(path2)


class TestReportLabPdfGeneratorGeneratePrescription:
    @pytest.fixture
    def generator(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PDF_OUTPUT_DIR", str(tmp_path))
        from app.core.config import get_settings

        get_settings.cache_clear()
        gen = ReportLabPdfGenerator()
        get_settings.cache_clear()
        return gen

    def test_generates_prescription_pdf(self, generator):
        rx = Prescription(
            id=21,
            consultation_id=12,
            doctor_id=6,
            patient_id=7,
            diagnosis="Test",
            medications=[
                Medication(
                    name="Amoxicillin",
                    dosage="500mg",
                    frequency="3x daily",
                    duration="7 days",
                )
            ],
            version=1,
        )
        artifact = generator.generate_prescription_pdf(rx)
        assert artifact.prescription_id == 21
        assert artifact.file_name.endswith(".pdf")
        assert artifact.storage_backend == "mongo_metadata"

    def test_prescription_pdf_storage_backend_is_mongo(self, generator):
        rx = Prescription(
            id=1, consultation_id=1, doctor_id=1, patient_id=1, diagnosis="X"
        )
        artifact = generator.generate_prescription_pdf(rx)
        assert artifact.storage_backend == "mongo_metadata"


# ── ConsultationMetadata validation ─────────────────────────────────────────


class TestConsultationMetadata:
    def test_valid_construction(self):
        meta = ConsultationMetadata(
            consultation_id=1,
            patient_name="Test",
            clinician_name="Dr. X",
            consultation_date=datetime.now(),
        )
        assert meta.consultation_id == 1

    def test_optional_fields_default_to_none(self):
        meta = ConsultationMetadata(
            consultation_id=5,
            patient_name="P",
            clinician_name="D",
            consultation_date=datetime.now(),
        )
        assert meta.patient_dob is None
        assert meta.visit_type is None


# ── ReportPdfArtifact validation ─────────────────────────────────────────────


class TestReportPdfArtifact:
    def test_valid_artifact(self):
        art = ReportPdfArtifact(
            file_path="/tmp/report.pdf",
            file_name="report.pdf",
            file_size_kb=12.5,
            generated_at=datetime.now(),
        )
        assert art.file_name == "report.pdf"
