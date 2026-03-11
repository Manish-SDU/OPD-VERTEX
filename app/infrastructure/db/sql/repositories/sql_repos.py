"""SQL repository stubs.

Gabriele and Mats: implement each class below. They receive a SQLAlchemy Session
and must translate between domain models (app/domain/*/models.py)
and ORM rows (app/infrastructure/db/sql/models/tables.py).

See TODO.md for step-by-step instructions.
"""

from __future__ import annotations


from sqlalchemy.orm import Session

from app.domain.audit.models import AuditLog, AuditLogRepository
from app.domain.auth.models import Staff, StaffRepository
from app.domain.consultations.models import Consultation, ConsultationRepository, ConsultationStatus
from app.domain.patients.models import Patient, PatientCreateRequest, PatientRepository
from app.domain.prescriptions.models import Prescription, PrescriptionRepository
from app.infrastructure.db.sql.models.tables import StaffRow, PatientRow, ConsultationRow, PrescriptionRow, AuditLogRow

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
class SqlStaffRepository(StaffRepository):
	def __init__(self, session: Session) -> None:
		self.session = session

	def get_by_email(self, email: str) -> Staff | None:
		row = self.session.query(StaffRow).filter_by(email=email).first()
		if row is None:
			return None
		return Staff(
			id=row.staff_id,
			first_name=row.first_name,
			last_name=row.last_name,
			email=row.email,
			password_hash=row.password_hash,
			specialization=row.specialization,
			license_number=row.license_number,
			phone=row.phone,
			role=row.role,
			is_active=row.is_active,
			created_at=row.created_at,
			updated_at=row.updated_at,
		)

	def get_by_id(self, staff_id: int) -> Staff | None:
		row = self.session.query(StaffRow).filter_by(staff_id=staff_id).first()
		if row is None:
			return None
		return Staff(
			id=row.staff_id,
			first_name=row.first_name,
			last_name=row.last_name,
			email=row.email,
			password_hash=row.password_hash,
			specialization=row.specialization,
			license_number=row.license_number,
			phone=row.phone,
			role=row.role,
			is_active=row.is_active,
			created_at=row.created_at,
			updated_at=row.updated_at,
		)

# ── SqlPatientRepository ─────────────────────────────────────────────
class SqlPatientRepository(PatientRepository):
	def __init__(self, session: Session) -> None:
		self.session = session

	def list_all(self) -> list[Patient]:
		rows = self.session.query(PatientRow).all()
		return [Patient(
			id=row.patient_id,
			first_name=row.first_name,
			last_name=row.last_name,
			date_of_birth=row.date_of_birth.date() if hasattr(row.date_of_birth, 'date') else row.date_of_birth,
			gender=row.gender,
			email=row.email,
			phone=row.phone,
			address=row.address,
			emergency_contact=row.emergency_contact,
			blood_type=row.blood_type,
			allergies=row.allergies,
			medical_history=row.medical_history,
			insurance_id=row.insurance_id,
			created_at=row.created_at,
			updated_at=row.updated_at,
		) for row in rows]

	def get_by_id(self, patient_id: int) -> Patient | None:
		row = self.session.query(PatientRow).filter_by(patient_id=patient_id).first()
		if row is None:
			return None
		return Patient(
			id=row.patient_id,
			first_name=row.first_name,
			last_name=row.last_name,
			date_of_birth=row.date_of_birth.date() if hasattr(row.date_of_birth, 'date') else row.date_of_birth,
			gender=row.gender,
			email=row.email,
			phone=row.phone,
			address=row.address,
			emergency_contact=row.emergency_contact,
			blood_type=row.blood_type,
			allergies=row.allergies,
			medical_history=row.medical_history,
			insurance_id=row.insurance_id,
			created_at=row.created_at,
			updated_at=row.updated_at,
		)

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
		)
		self.session.add(row)
		self.session.commit()
		self.session.refresh(row)
		return Patient(
			id=row.patient_id,
			first_name=row.first_name,
			last_name=row.last_name,
			date_of_birth=row.date_of_birth.date() if hasattr(row.date_of_birth, 'date') else row.date_of_birth,
			gender=row.gender,
			email=row.email,
			phone=row.phone,
			address=row.address,
			emergency_contact=row.emergency_contact,
			blood_type=row.blood_type,
			allergies=row.allergies,
			medical_history=row.medical_history,
			insurance_id=row.insurance_id,
			created_at=row.created_at,
			updated_at=row.updated_at,
		)

# ── SqlConsultationRepository ────────────────────────────────────────
class SqlConsultationRepository(ConsultationRepository):
	def __init__(self, session: Session) -> None:
		self.session = session

	def list_all(self) -> list[Consultation]:
		rows = self.session.query(ConsultationRow).all()
		return [self._to_domain(row) for row in rows]

	def get_by_id(self, consultation_id: int) -> Consultation | None:
		row = self.session.query(ConsultationRow).filter_by(consultation_id=consultation_id).first()
		return self._to_domain(row) if row else None

	def create(self, patient_id: int, doctor_id: int, status: str = "recording") -> Consultation:
		row = ConsultationRow(
			patient_id=patient_id,
			doctor_id=doctor_id,
			status=status,
			started_at=datetime.utcnow(),
		)
		self.session.add(row)
		self.session.commit()
		self.session.refresh(row)
		return self._to_domain(row)

	def update_status(self, consultation_id: int, status: str) -> Consultation | None:
		row = self.session.query(ConsultationRow).filter_by(consultation_id=consultation_id).first()
		if not row:
			return None
		row.status = status
		self.session.commit()
		self.session.refresh(row)
		return self._to_domain(row)

	def _to_domain(self, row: ConsultationRow) -> Consultation:
		return Consultation(
			id=row.consultation_id,
			doctor_id=row.doctor_id,
			patient_id=row.patient_id,
			status=row.status,
			started_at=row.started_at,
			ended_at=row.ended_at,
			approved_at=row.approved_at,
			transcript_doc_id=row.transcript_doc_id,
			notes_doc_id=row.notes_doc_id,
			created_at=row.created_at,
			updated_at=row.updated_at,
		)

# ── SqlPrescriptionRepository ────────────────────────────────────────
class SqlPrescriptionRepository(PrescriptionRepository):
	def __init__(self, session: Session) -> None:
		self.session = session

	def list_all(self) -> list[Prescription]:
		rows = self.session.query(PrescriptionRow).all()
		return [self._to_domain(row) for row in rows]

	def get_by_id(self, prescription_id: int) -> Prescription | None:
		row = self.session.query(PrescriptionRow).filter_by(prescription_id=prescription_id).first()
		return self._to_domain(row) if row else None

	def create(self, **kwargs) -> Prescription:
		row = PrescriptionRow(**kwargs)
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
			medications=row.medications,
			instructions=row.instructions,
			follow_up_date=row.follow_up_date,
			pdf_path=row.pdf_path,
			is_approved=row.is_approved,
			is_emailed=row.is_emailed,
			emailed_at=row.emailed_at,
			version=row.version,
			created_at=row.created_at,
			updated_at=row.updated_at,
		)

# ── SqlAuditLogRepository ────────────────────────────────────────────
class SqlAuditLogRepository(AuditLogRepository):
	def __init__(self, session: Session) -> None:
		self.session = session

	def list_recent(self) -> list[AuditLog]:
		rows = self.session.query(AuditLogRow).order_by(AuditLogRow.timestamp.desc()).limit(50).all()
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
			id=row.id,
			user_id=row.user_id,
			user_role=row.user_role,
			action=row.action,
			target_table=row.target_table,
			target_id=row.target_id,
			details=row.details,
			ip_address=row.ip_address,
			timestamp=row.timestamp,
		)
