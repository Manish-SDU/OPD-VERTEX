"""PDF generation application service."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.domain.pdf.models import (
    ConsultationMetadata,
    ReportPdfArtifact,
    PdfGenerator,
)

if TYPE_CHECKING:
    from app.infrastructure.persistence.repositories import (
        GeneratedDocumentRepository,
        ConsultationRepository,
        PatientRepository,
        StaffRepository,
    )


class ReportPdfApplicationService:
    """Orchestrates PDF report generation."""

    def __init__(
        self,
        generated_repository: GeneratedDocumentRepository,
        consultation_repository: ConsultationRepository,
        pdf_generator: PdfGenerator,
        patient_repository: PatientRepository | None = None,
        staff_repository: StaffRepository | None = None,
        logger: logging.Logger | None = None,
    ):
        self.generated_repository = generated_repository
        self.consultation_repository = consultation_repository
        self.pdf_generator = pdf_generator
        self.patient_repository = patient_repository
        self.staff_repository = staff_repository
        self.logger = logger or logging.getLogger(__name__)

    def generate_report_pdf(self, consultation_id: int) -> ReportPdfArtifact:
        """Generate clinical report PDF.

        Args:
            consultation_id: The consultation ID to generate PDF for

        Returns:
            ReportPdfArtifact with file path and metadata

        Raises:
            ValueError: If report markdown is empty or not found
            IOError: If PDF generation fails
        """
        self.logger.info(f"Generating PDF for consultation {consultation_id}")

        # Fetch generated clinical notes from MongoDB
        generated_doc = self.generated_repository.get_by_consultation_id(
            consultation_id
        )
        if not generated_doc:
            self.logger.warning(
                f"No generated document found for consultation {consultation_id}"
            )
            raise ValueError(
                f"No clinical report found for consultation {consultation_id}"
            )

        if not generated_doc.generated_output.report_markdown:
            self.logger.warning(
                f"Report markdown is empty for consultation {consultation_id}"
            )
            raise ValueError(
                f"Report markdown is empty for consultation {consultation_id}"
            )

        # Fetch consultation metadata from MySQL
        consultation = self.consultation_repository.get_by_id(consultation_id)
        if not consultation:
            self.logger.warning(f"Consultation {consultation_id} not found")
            raise ValueError(f"Consultation {consultation_id} not found")

        # Fetch patient and clinician info
        # Prefer explicit repositories (works for both mock and SQL modes).
        # Fall back to ORM relationship attributes for SQL-only setups.
        if self.patient_repository is not None:
            patient = self.patient_repository.get_by_id(consultation.patient_id)
        else:
            patient = getattr(consultation, "patient", None)

        if self.staff_repository is not None:
            clinician = self.staff_repository.get_by_id(consultation.doctor_id)
        else:
            clinician = getattr(consultation, "clinician", None)

        if not patient or not clinician:
            self.logger.warning(
                f"Missing patient or clinician for consultation {consultation_id}"
            )
            raise ValueError("Missing patient or clinician information")

        # Build consultation metadata
        metadata = ConsultationMetadata(
            consultation_id=consultation_id,
            patient_name=f"{patient.first_name} {patient.last_name}",
            patient_dob=patient.date_of_birth.isoformat()
            if patient.date_of_birth
            else None,
            clinician_name=f"{clinician.first_name} {clinician.last_name}",
            consultation_date=consultation.started_at,
            visit_type=consultation.visit_type or "General",
        )

        # Generate PDF
        file_path = self.pdf_generator.generate_report_pdf(
            generated_doc.generated_output.report_markdown, metadata
        )

        self.logger.info(f"PDF generated successfully at {file_path}")

        # Return artifact
        from pathlib import Path
        from datetime import datetime

        path_obj = Path(file_path)
        return ReportPdfArtifact(
            file_path=file_path,
            file_name=path_obj.name,
            file_size_kb=path_obj.stat().st_size / 1024,
            generated_at=datetime.now(),
        )
