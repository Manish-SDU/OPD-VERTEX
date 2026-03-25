from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date

from app.domain.prescriptions.models import Medication, Prescription
from app.infrastructure.db.sql.models.tables import (
    AuditLogRow,
    ConsultationRow,
    PatientRow,
    PrescriptionRow,
)
from app.infrastructure.db.sql.repositories.sql_repos import (
    SqlAuditLogRepository,
    SqlConsultationRepository,
    SqlPrescriptionRepository,
)
from app.infrastructure.pdf.reportlab_adapter import ReportLabPdfGenerator


class TestSqlSchemaAlignment:
    def test_prescriptions_table_does_not_store_pdf_path(self):
        assert "pdf_path" not in PrescriptionRow.__table__.columns

    def test_consultations_table_does_not_store_mongo_doc_ids(self):
        assert "transcript_doc_id" not in ConsultationRow.__table__.columns
        assert "notes_doc_id" not in ConsultationRow.__table__.columns

    def test_date_columns_match_domain_expectations(self):
        assert isinstance(
            PatientRow.__table__.columns["date_of_birth"].type,
            Date,
        )
        assert isinstance(
            PrescriptionRow.__table__.columns["follow_up_date"].type,
            Date,
        )

    def test_prescriptions_table_has_version_uniqueness(self):
        constraint_names = {
            constraint.name for constraint in PrescriptionRow.__table__.constraints
        }
        assert "uq_prescriptions_consultation_version" in constraint_names


class TestSqlRepositoryMappings:
    def test_prescription_row_maps_json_to_domain_medications(self):
        repo = SqlPrescriptionRepository(session=None)  # type: ignore[arg-type]
        row = PrescriptionRow(
            prescription_id=10,
            consultation_id=3,
            doctor_id=4,
            patient_id=5,
            diagnosis="Hypertension",
            medications=[
                {
                    "name": "Lisinopril",
                    "dosage": "10 mg",
                    "frequency": "once daily",
                    "duration": "30 days",
                    "route": "oral",
                }
            ],
            follow_up_date=date(2026, 4, 1),
            version=2,
            is_approved=True,
            is_emailed=False,
        )

        prescription = repo._to_domain(row)

        assert isinstance(prescription.medications[0], Medication)
        assert prescription.medications[0].name == "Lisinopril"
        assert prescription.follow_up_date == date(2026, 4, 1)

    def test_consultation_row_maps_without_mongo_doc_fields(self):
        repo = SqlConsultationRepository(session=None)  # type: ignore[arg-type]
        row = ConsultationRow(
            consultation_id=11,
            doctor_id=2,
            patient_id=8,
            status="approved",
            started_at=datetime(2026, 3, 25, 10, 0, 0),
            approved_at=datetime(2026, 3, 25, 10, 30, 0),
        )

        consultation = repo._to_domain(row)

        assert consultation.id == 11
        assert consultation.doctor_id == 2
        assert not hasattr(consultation, "transcript_doc_id")

    def test_audit_row_maps_log_id_to_domain_id(self):
        repo = SqlAuditLogRepository(session=None)  # type: ignore[arg-type]
        row = AuditLogRow(
            log_id=99,
            user_id=1,
            user_role="doctor",
            action="APPROVE",
        )

        audit_log = repo._to_domain(row)

        assert audit_log.id == 99


class TestPdfArtifactOwnership:
    def test_reportlab_adapter_returns_mongo_side_artifact_metadata(self):
        artifact = ReportLabPdfGenerator().generate_prescription_pdf(
            Prescription(
                id=21,
                consultation_id=12,
                doctor_id=6,
                patient_id=7,
                diagnosis="Test",
                medications=[],
                version=3,
            )
        )

        assert artifact.prescription_id == 21
        assert artifact.consultation_id == 12
        assert artifact.version == 3
        assert artifact.storage_backend == "mongo_metadata"
