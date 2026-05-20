"""SQL repository stubs.

Gabriele and Mats: implement each class below. They receive a SQLAlchemy Session
and must translate between domain models (app/domain/*/models.py)
and ORM rows (app/infrastructure/db/sql/models/tables.py).

See TODO.md for step-by-step instructions.
"""

from __future__ import annotations
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.appointments.models import (
    Appointment,
    AppointmentCreateRequest,
    AppointmentRepository,
    AppointmentStatus,
)
from app.domain.audit.models import AuditLog, AuditLogRepository
from app.domain.auth.models import Staff, StaffCreateRequest, StaffRepository
from app.domain.consultations.models import (
    Consultation,
    ConsultationRepository,
    ConsultationStatus,
)
from app.domain.patients.models import Patient, PatientCreateRequest, PatientRepository
from app.domain.prescriptions.models import (
    Medication,
    Prescription,
    PrescriptionRepository,
)
from app.infrastructure.db.sql.models.tables import (
    AppointmentRow,
    StaffRow,
    PatientRow,
    ConsultationRow,
    PrescriptionRow,
    AuditLogRow,
)
from app.infrastructure.logging import apply_logging_aspect

# ── Example pattern (repeat for each repository) ───────────────────────
#
#   class SqlStaffRepository(StaffRepository):
#       def __init__(self, session: Session) -> None:
#           self.session = session
#
#       def get_by_email(self, email: str) -> Staff | None:
#           row = self.session.query(StaffRow).filter_by(email=email).first()
#           if row is None:
#               return None
#           return Staff(id=row.staff_id, first_name=row.first_name, ...)
#


# ── SqlStaffRepository ───────────────────────────────────────────────
@apply_logging_aspect("repository", "staff")
class SqlStaffRepository(StaffRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def _to_domain(self, row: StaffRow) -> Staff:
        return Staff(
            id=row.staff_id,
            first_name=row.first_name,
            last_name=row.last_name,
            email=row.email,
            phone=row.phone,
            password_hash=row.password_hash,
            role=row.role,
            license_number=row.license_number,
            specialization=row.specialization,
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_all(self) -> list[Staff]:
        rows = self.session.query(StaffRow).all()
        return [self._to_domain(row) for row in rows]

    def get_by_email(self, email: str) -> Staff | None:
        row = self.session.query(StaffRow).filter_by(email=email).first()
        if row is None:
            return None
        return self._to_domain(row)

    def get_by_id(self, staff_id: int) -> Staff | None:
        row = self.session.query(StaffRow).filter_by(staff_id=staff_id).first()
        if row is None:
            return None
        return self._to_domain(row)

    def create(self, req: StaffCreateRequest) -> Staff:
        row = StaffRow(
            first_name=req.first_name,
            last_name=req.last_name,
            email=req.email,
            phone=req.phone,
            password_hash=req.password_hash,
            role=req.role,
            is_active=True,
            specialization=req.specialization,
            license_number=req.license_number,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return self._to_domain(row)


# ── SqlPatientRepository ─────────────────────────────────────────────
@apply_logging_aspect("repository", "patients")
class SqlPatientRepository(PatientRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def _to_domain(self, row: PatientRow) -> Patient:
        return Patient(
            id=row.patient_id,
            first_name=row.first_name,
            last_name=row.last_name,
            date_of_birth=row.date_of_birth,
            gender=row.gender,
            email=row.email,
            phone=row.phone,
            address=row.address,
            emergency_contact=row.emergency_contact,
            blood_type=row.blood_type,
            allergies=row.allergies,
            medical_history=row.medical_history,
            insurance_id=row.insurance_id,
            password_hash=row.password_hash,
            role=row.role,
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_all(self) -> list[Patient]:
        rows = self.session.query(PatientRow).all()
        return [self._to_domain(row) for row in rows]

    def get_by_id(self, patient_id: int) -> Patient | None:
        row = self.session.query(PatientRow).filter_by(patient_id=patient_id).first()
        if row is None:
            return None
        return self._to_domain(row)

    def get_by_email(self, email: str) -> Patient | None:
        row = self.session.query(PatientRow).filter_by(email=email).first()
        if row is None:
            return None
        return self._to_domain(row)

    def create(self, req: PatientCreateRequest) -> Patient:
        row = PatientRow(
            first_name=req.first_name,
            last_name=req.last_name,
            date_of_birth=req.date_of_birth,
            gender=req.gender,
            email=req.email,
            phone=req.phone,
            allergies=req.allergies,
            medical_history=req.medical_history,
            password_hash=req.password_hash,
            role="patient",
            is_active=True,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return self._to_domain(row)


# ── SqlConsultationRepository ────────────────────────────────────────
@apply_logging_aspect("repository", "consultations")
class SqlConsultationRepository(ConsultationRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[Consultation]:
        rows = self.session.query(ConsultationRow).all()
        return [self._to_domain(row) for row in rows]

    def get_by_id(self, consultation_id: int) -> Consultation | None:
        row = (
            self.session.query(ConsultationRow)
            .filter_by(consultation_id=consultation_id)
            .first()
        )
        return self._to_domain(row) if row else None

    def create(self, consultation: Consultation) -> Consultation:
        row = ConsultationRow(
            patient_id=consultation.patient_id,
            doctor_id=consultation.doctor_id,
            status=consultation.status.value,
            started_at=consultation.started_at or datetime.utcnow(),
            ended_at=consultation.ended_at,
            approved_at=consultation.approved_at,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return self._to_domain(row)

    def update_status(self, consultation_id: int, status: ConsultationStatus) -> None:
        row = (
            self.session.query(ConsultationRow)
            .filter_by(consultation_id=consultation_id)
            .first()
        )
        if not row:
            return
        row.status = status.value
        if status == ConsultationStatus.APPROVED:
            row.approved_at = datetime.utcnow()
        self.session.commit()

    def _to_domain(self, row: ConsultationRow) -> Consultation:
        return Consultation(
            id=row.consultation_id,
            doctor_id=row.doctor_id,
            patient_id=row.patient_id,
            status=ConsultationStatus(row.status),
            started_at=row.started_at,
            ended_at=row.ended_at,
            approved_at=row.approved_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


# ── SqlPrescriptionRepository ────────────────────────────────────────
@apply_logging_aspect("repository", "prescriptions")
class SqlPrescriptionRepository(PrescriptionRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[Prescription]:
        rows = self.session.query(PrescriptionRow).all()
        return [self._to_domain(row) for row in rows]

    def get_by_id(self, prescription_id: int) -> Prescription | None:
        row = (
            self.session.query(PrescriptionRow)
            .filter_by(prescription_id=prescription_id)
            .first()
        )
        return self._to_domain(row) if row else None

    def create(self, prescription: Prescription) -> Prescription:
        row = PrescriptionRow(
            consultation_id=prescription.consultation_id,
            doctor_id=prescription.doctor_id,
            patient_id=prescription.patient_id,
            diagnosis=prescription.diagnosis,
            medications=[
                medication.model_dump() for medication in prescription.medications
            ],
            instructions=prescription.instructions,
            follow_up_date=prescription.follow_up_date,
            is_approved=prescription.is_approved,
            is_emailed=prescription.is_emailed,
            emailed_at=prescription.emailed_at,
            version=prescription.version,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return self._to_domain(row)

    def _to_domain(self, row: PrescriptionRow) -> Prescription:
        return Prescription(
            id=row.prescription_id,
            consultation_id=row.consultation_id,
            doctor_id=row.doctor_id,
            patient_id=row.patient_id,
            diagnosis=row.diagnosis,
            medications=[Medication.model_validate(item) for item in row.medications],
            instructions=row.instructions,
            follow_up_date=row.follow_up_date,
            is_approved=row.is_approved,
            is_emailed=row.is_emailed,
            emailed_at=row.emailed_at,
            version=row.version,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


# ── SqlAuditLogRepository ────────────────────────────────────────────
@apply_logging_aspect("repository", "audit")
class SqlAuditLogRepository(AuditLogRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_recent(self) -> list[AuditLog]:
        rows = (
            self.session.query(AuditLogRow)
            .order_by(AuditLogRow.timestamp.desc())
            .limit(50)
            .all()
        )
        return [self._to_domain(row) for row in rows]

    def append(self, entry: AuditLog) -> AuditLog:
        row = AuditLogRow(
            user_id=entry.user_id,
            user_role=entry.user_role,
            action=entry.action,
            target_table=entry.target_table,
            target_id=entry.target_id,
            details=entry.details,
            ip_address=entry.ip_address,
            timestamp=entry.timestamp or datetime.utcnow(),
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return self._to_domain(row)

    def _to_domain(self, row: AuditLogRow) -> AuditLog:
        return AuditLog(
            id=row.log_id,
            user_id=row.user_id,
            user_role=row.user_role,
            action=row.action,
            target_table=row.target_table,
            target_id=row.target_id,
            details=row.details,
            ip_address=row.ip_address,
            timestamp=row.timestamp,
        )


# ── SqlAppointmentRepository ─────────────────────────────────────────
@apply_logging_aspect("repository", "appointments")
class SqlAppointmentRepository(AppointmentRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def _to_domain(self, row: AppointmentRow) -> Appointment:
        return Appointment(
            id=row.appointment_id,
            patient_id=row.patient_id,
            doctor_id=row.doctor_id,
            scheduled_at=row.scheduled_at,
            duration_minutes=row.duration_minutes,
            status=AppointmentStatus(row.status),
            reason=row.reason,
            notes=row.notes,
            consultation_id=row.consultation_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _priority_order(self):
        from sqlalchemy import case

        return (
            case(
                (AppointmentRow.status == "confirmed", 0),
                (AppointmentRow.status == "pending", 1),
                else_=2,
            ),
            AppointmentRow.scheduled_at,
            AppointmentRow.created_at,
        )

    def list_all(self) -> list[Appointment]:
        rows = (
            self.session.query(AppointmentRow).order_by(*self._priority_order()).all()
        )
        return [self._to_domain(r) for r in rows]

    def get_by_id(self, appointment_id: int) -> Appointment | None:
        row = (
            self.session.query(AppointmentRow)
            .filter_by(appointment_id=appointment_id)
            .first()
        )
        return self._to_domain(row) if row else None

    def list_by_patient(self, patient_id: int) -> list[Appointment]:
        rows = (
            self.session.query(AppointmentRow)
            .filter_by(patient_id=patient_id)
            .order_by(*self._priority_order())
            .all()
        )
        return [self._to_domain(r) for r in rows]

    def list_by_doctor(self, doctor_id: int) -> list[Appointment]:
        rows = (
            self.session.query(AppointmentRow)
            .filter_by(doctor_id=doctor_id)
            .order_by(*self._priority_order())
            .all()
        )
        return [self._to_domain(r) for r in rows]

    def create(self, request: AppointmentCreateRequest) -> Appointment:
        row = AppointmentRow(
            patient_id=request.patient_id,
            doctor_id=request.doctor_id,
            scheduled_at=request.scheduled_at,
            duration_minutes=request.duration_minutes,
            status="pending",
            reason=request.reason,
            notes=request.notes,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return self._to_domain(row)

    def update_status(
        self, appointment_id: int, status: AppointmentStatus
    ) -> Appointment | None:
        row = (
            self.session.query(AppointmentRow)
            .filter_by(appointment_id=appointment_id)
            .first()
        )
        if not row:
            return None
        row.status = status.value
        self.session.commit()
        self.session.refresh(row)
        return self._to_domain(row)

    def cancel(self, appointment_id: int) -> Appointment | None:
        return self.update_status(appointment_id, AppointmentStatus.CANCELLED)

    def link_consultation(
        self, appointment_id: int, consultation_id: int
    ) -> Appointment | None:
        row = (
            self.session.query(AppointmentRow)
            .filter_by(appointment_id=appointment_id)
            .first()
        )
        if not row:
            return None
        row.consultation_id = consultation_id
        self.session.commit()
        self.session.refresh(row)
        return self._to_domain(row)
