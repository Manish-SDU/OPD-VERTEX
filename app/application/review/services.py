"""Review workflow application service."""

from __future__ import annotations

from datetime import date
from pathlib import Path

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
from app.domain.email.models import EmailMessage, EmailAttachment


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
        pdf_app_service=None,
    ) -> None:
        self.consultation_repository = consultation_repository
        self.consultation_doc_repository = consultation_doc_repository
        self.generated_repository = generated_repository
        self.prescription_repository = prescription_repository
        self.patient_repository = patient_repository
        self.email_service = email_service
        self.pdf_app_service = pdf_app_service

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
        """
        Send a patient-friendly summary email with prescription, follow-up, and suggestions.
        PDF attachment is included.
        """
        generated_document = self.generated_repository.get_by_consultation_id(
            consultation_id
        )
        if generated_document is None:
            raise ValueError("Generated report not found.")

        if generated_document.status != GeneratedDocumentStatus.APPROVED:
            raise ValueError("Only approved reports can be emailed.")

        patient = self.patient_repository.get_by_id(generated_document.patient_id)
        if patient is None:
            raise ValueError("Patient not found.")

        if not getattr(patient, "email", None):
            raise ValueError("Patient email is missing.")

        pdf_dir = Path(__file__).resolve().parents[3] / "storage" / "pdfs"
        matches = sorted(
            pdf_dir.glob(f"*_{consultation_id}.pdf"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not matches:
            raise ValueError(
                "PDF has not been exported yet. Please export the PDF first before sending to patient."
            )
        pdf_path = matches[0]

        pdf_attachment = EmailAttachment(
            filename=pdf_path.name,
            content_type="application/pdf",
            data=pdf_path.read_bytes(),
        )

        notes = generated_document.generated_output
        clinician_name = (
            getattr(getattr(notes, "encounter_info", None), "clinician_name", "")
            or "Your clinician"
        )

        content = self._build_patient_email_content(notes)
        body = self._build_patient_email_body(
            patient_name=f"{patient.first_name} {patient.last_name}".strip(),
            clinician_name=clinician_name,
            content=content,
        )

        message = EmailMessage(
            to_email=patient.email,
            to_name=f"{patient.first_name} {patient.last_name}".strip(),
            subject=f"Your consultation summary (#{consultation_id})",
            text_body=body,
            html_body=None,
            attachment=pdf_attachment,
        )

        return self.email_service.send_email(message)

    def _build_patient_email_content(self, notes) -> dict[str, str]:
        """
        Extract patient-facing parts:
        - prescription (medications)
        - follow-up steps
        - suggestions (instructions + referrals/tests/imaging)
        """

        def _attr(obj, *names, default=None):
            for name in names:
                if hasattr(obj, name):
                    value = getattr(obj, name)
                    if value is not None:
                        return value
            return default

        prescription_lines: list[str] = []

        # Medications
        meds = _attr(notes, "medications", default=[]) or []
        for med in meds:
            parts = []
            name = _attr(med, "name", default="")
            if name:
                parts.append(name)
            dosage = _attr(med, "dosage", "dose", default="")
            if dosage:
                parts.append(f"dose: {dosage}")
            route = _attr(med, "route", default="")
            if route:
                parts.append(f"route: {route}")
            frequency = _attr(med, "frequency", default="")
            if frequency:
                parts.append(f"frequency: {frequency}")
            duration = _attr(med, "duration", default="")
            if duration:
                parts.append(f"duration: {duration}")
            special = _attr(
                med, "special_instructions", "specialinstructions", default=""
            )
            if special:
                parts.append(f"instructions: {special}")

            if parts:
                prescription_lines.append("- " + ", ".join(parts))

        # Follow-up
        follow_up = (
            (_attr(notes, "follow_up", "followup", default="") or "")
            or (
                _attr(
                    getattr(notes, "plan", object()),
                    "follow_up",
                    "followup",
                    default="",
                )
                or ""
            )
        ).strip()

        # Suggestions
        suggestions_parts: list[str] = []

        pi = (
            _attr(notes, "patient_instructions", "patientinstructions", default="")
            or ""
        ).strip()
        if not pi and hasattr(notes, "plan"):
            pi = (
                _attr(
                    notes.plan,
                    "patient_instructions",
                    "patientinstructions",
                    default="",
                )
                or ""
            ).strip()

        if pi:
            suggestions_parts.append(pi)

        # Referrals
        referrals = []
        if hasattr(notes, "plan"):
            referrals = _attr(notes.plan, "referrals", default=[]) or []
        if referrals:
            suggestions_parts.append(
                "Referrals:\n" + "\n".join(f"- {item}" for item in referrals)
            )

        # Lab tests
        lab_tests = (
            _attr(notes, "lab_tests_ordered", "labtestsordered", default=[]) or []
        )
        if lab_tests:
            suggestions_parts.append(
                "Lab tests:\n" + "\n".join(f"- {item}" for item in lab_tests)
            )

        # Imaging
        imaging = []
        if hasattr(notes, "plan"):
            imaging = (
                _attr(notes.plan, "imaging_ordered", "imagingordered", default=[]) or []
            )
        if imaging:
            suggestions_parts.append(
                "Imaging:\n" + "\n".join(f"- {item}" for item in imaging)
            )

        return {
            "prescription": "\n".join(prescription_lines)
            or "No prescription provided.",
            "follow_up_steps": follow_up or "No follow-up steps provided.",
            "suggestions": "\n\n".join(suggestions_parts)
            or "No additional suggestions provided.",
        }

    def _build_patient_email_body(
        self,
        patient_name: str,
        clinician_name: str,
        content: dict[str, str],
    ) -> str:
        return (
            f"Dear {patient_name},\n\n"
            "Here is your treatment information from your consultation.\n\n"
            f"Prescription:\n{content['prescription']}\n\n"
            f"Follow-up steps:\n{content['follow_up_steps']}\n\n"
            f"Suggestions:\n{content['suggestions']}\n\n"
            "Best regards,\n"
            f"{clinician_name}"
        )
