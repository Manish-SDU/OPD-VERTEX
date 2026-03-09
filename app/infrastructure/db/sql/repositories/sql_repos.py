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
# Each method should:
#   1. Query/insert/update via the ORM row classes in tables.py
#   2. Convert the ORM row to/from the domain Pydantic model
#   3. Return the domain model
