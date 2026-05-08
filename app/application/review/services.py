"""Review workflow application service."""

from __future__ import annotations

from datetime import date

from app.domain.clinical_notes.models import (
    ConsultationDocument,
    ConsultationDocumentRepository,
    GeneratedDocument,
    GeneratedDocumentRepository,
    GeneratedDocumentStatus,
)
from app.domain.common.types import utcnow
from app.domain.consultations.models import ConsultationRepository, ConsultationStatus
from app.domain.prescriptions.models import Prescription, PrescriptionRepository
from app.domain.suggestive_mode.models import SuggestiveReview
from app.infrastructure.logging import apply_logging_aspect
from app.domain.email.models import EmailAttachment, EmailMessage


@apply_logging_aspect("service", "review")
class ReviewApplicationService:
    def __init__(
        self,
        consultation_repository: ConsultationRepository,
        consultation_doc_repository: ConsultationDocumentRepository,
        generated_repository: GeneratedDocumentRepository,
        prescription_repository: PrescriptionRepository,
        patient_repository,
        email_service,
    ) -> None:
        self.consultation_repository = consultation_repository
        self.consultation_doc_repository = consultation_doc_repository
        self.generated_repository = generated_repository
        self.prescription_repository = prescription_repository
        self.patient_repository = patient_repository
        self.email_service = email_service

    def build_review_context(
        self, consultation_id: int
    ) -> tuple[ConsultationDocument | None, GeneratedDocument | None, SuggestiveReview]:
        consultation_document = self.consultation_doc_repository.get_by_consultation_id(
            consultation_id
        )
        generated_document = self.generated_repository.get_by_consultation_id(
            consultation_id
        )
        suggestive_review = (
            generated_document.suggestive_output
            if generated_document and generated_document.suggestive_output
            else SuggestiveReview(
                consultation_id=consultation_id,
                summary="Suggestive review has not been generated yet.",
            )
        )
        return consultation_document, generated_document, suggestive_review

    def approve_review(self, consultation_id: int) -> Prescription:
        consultation = self.consultation_repository.get_by_id(consultation_id)
        if consultation is None:
            raise ValueError(f"Consultation {consultation_id} was not found.")

        generated_document = self.generated_repository.get_by_consultation_id(
            consultation_id
        )
        if generated_document is None:
            raise ValueError(
                f"Consultation {consultation_id} does not have a generated draft."
            )

        existing_prescription = self._find_latest_prescription_for_consultation(
            consultation_id
        )
        if (
            generated_document.status == GeneratedDocumentStatus.APPROVED
            and existing_prescription
        ):
            return existing_prescription

        version = (
            1 if existing_prescription is None else existing_prescription.version + 1
        )
        prescription = Prescription(
            consultation_id=consultation_id,
            doctor_id=generated_document.doctor_id,
            patient_id=generated_document.patient_id,
            diagnosis=generated_document.generated_output.diagnosis
            or "Not established",
            medications=generated_document.generated_output.medications,
            instructions=generated_document.generated_output.patient_instructions
            or "No additional instructions provided.",
            follow_up_date=self._parse_follow_up_date(
                generated_document.generated_output.follow_up
            ),
            is_approved=True,
            version=version,
        )
        saved_prescription = self.prescription_repository.create(prescription)

        now = utcnow()
        generated_document.status = GeneratedDocumentStatus.APPROVED
        generated_document.approved_at = now
        generated_document.updated_at = now
        self.generated_repository.save(generated_document)

        self.consultation_repository.update_status(
            consultation_id, ConsultationStatus.APPROVED
        )
        return saved_prescription

    def reject_review(self, consultation_id: int) -> GeneratedDocument | None:
        generated_document = self.generated_repository.get_by_consultation_id(
            consultation_id
        )
        if generated_document is None:
            self.consultation_repository.update_status(
                consultation_id, ConsultationStatus.REJECTED
            )
            return None

        generated_document.status = GeneratedDocumentStatus.REJECTED
        generated_document.updated_at = utcnow()
        saved_document = self.generated_repository.save(generated_document)
        self.consultation_repository.update_status(
            consultation_id, ConsultationStatus.REJECTED
        )
        return saved_document

    def update_report_markdown(
        self, consultation_id: int, markdown: str
    ) -> GeneratedDocument:
        """Update the report_markdown field of a generated document."""
        generated_document = self.generated_repository.get_by_consultation_id(
            consultation_id
        )
        if generated_document is None:
            raise ValueError(
                f"Consultation {consultation_id} does not have a generated document."
            )

        generated_document.generated_output.report_markdown = markdown
        generated_document.updated_at = utcnow()
        return self.generated_repository.save(generated_document)

    def _find_latest_prescription_for_consultation(
        self, consultation_id: int
    ) -> Prescription | None:
        matching = [
            prescription
            for prescription in self.prescription_repository.list_all()
            if prescription.consultation_id == consultation_id
        ]
        if not matching:
            return None
        return sorted(matching, key=lambda item: item.version)[-1]

    def _parse_follow_up_date(self, value: str) -> date | None:
        cleaned = value.strip()
        if not cleaned or cleaned.lower() in {
            "not specified",
            "not recorded",
            "unknown",
        }:
            return None
        try:
            return date.fromisoformat(cleaned)
        except ValueError:
            return None
    
    def send_report_to_patient(self, consultation_id: int) -> dict:
        generated_document = self.generated_repository.get_by_consultation_id(consultation_id)
        if generated_document is None:
            raise ValueError("Generated report not found.")

        if str(generated_document.status).lower() != "approved":
            raise ValueError("Only approved reports can be emailed.")

        patient = self.patient_repository.get_by_id(generated_document.patient_id)
        if patient is None:
            raise ValueError("Patient not found.")

        if not getattr(patient, "email", None):
            raise ValueError("Patient email is missing.")

        pdf_bytes = b"%PDF-1.4 fake pdf bytes for now"

        message = EmailMessage(
            to_email=patient.email,
            to_name=f"{patient.first_name} {patient.last_name}".strip(),
            subject=f"Clinical Report #{consultation_id}",
            text_body="Please find your approved clinical report attached.",
            attachment=EmailAttachment(
                filename=f"clinical-report-{consultation_id}.pdf",
                content_type="application/pdf",
                data=pdf_bytes,
            ),
        )

        return self.email_service.send_email(message)
