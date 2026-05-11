"""Unit tests for in-memory repository implementations."""

from datetime import date

from app.domain.audit.models import AuditLog
from app.domain.consultations.models import Consultation, ConsultationStatus
from app.domain.patients.models import PatientCreateRequest
from app.domain.prescriptions.models import Medication, Prescription


# ── Staff Repository ───────────────────────────────────────────────────


class TestInMemoryStaffRepository:
    def test_seeded_staff_exist(self, staff_repo):
        doctor = staff_repo.get_by_email("doctor@example.local")
        assert doctor is not None
        assert doctor.role == "doctor"

    def test_get_by_email_returns_none_for_unknown(self, staff_repo):
        assert staff_repo.get_by_email("nobody@example.local") is None

    def test_get_by_id_returns_staff(self, staff_repo):
        admin = staff_repo.get_by_id(2)
        assert admin is not None
        assert admin.role == "admin"

    def test_get_by_id_returns_none_for_unknown(self, staff_repo):
        assert staff_repo.get_by_id(999) is None


# ── Patient Repository ────────────────────────────────────────────────


class TestInMemoryPatientRepository:
    def test_list_all_returns_seeded_patients(self, patient_repository):
        patients = patient_repository.list_all()
        assert len(patients) >= 2

    def test_get_by_id_returns_patient(self, patient_repository):
        patient = patient_repository.get_by_id(1)
        assert patient is not None
        assert patient.first_name == "Giulia"

    def test_get_by_id_returns_none_for_unknown(self, patient_repository):
        assert patient_repository.get_by_id(999) is None

    def test_create_assigns_id_and_persists(self, patient_repository):
        req = PatientCreateRequest(
            first_name="Test",
            last_name="User",
            date_of_birth=date(2000, 1, 1),
            email="test@example.local",
            password_hash="dummy",
        )
        patient = patient_repository.create(req)
        assert patient.id is not None
        assert patient_repository.get_by_id(patient.id) is not None

    def test_create_increments_id(self, patient_repository):
        initial_count = len(patient_repository.list_all())
        req = PatientCreateRequest(
            first_name="A",
            last_name="B",
            date_of_birth=date(1990, 1, 1),
            email="a@b.com",
            password_hash="x",
        )
        patient_repository.create(req)
        assert len(patient_repository.list_all()) == initial_count + 1


# ── Consultation Repository ───────────────────────────────────────────


class TestInMemoryConsultationRepository:
    def test_list_all_returns_seeded(self, consultation_repo):
        assert len(consultation_repo.list_all()) >= 2

    def test_get_by_id(self, consultation_repo):
        c = consultation_repo.get_by_id(1)
        assert c is not None
        assert c.status == ConsultationStatus.REVIEW

    def test_create_consultation(self, consultation_repo):
        c = Consultation(doctor_id=1, patient_id=1, status=ConsultationStatus.RECORDING)
        created = consultation_repo.create(c)
        assert created.id is not None
        assert consultation_repo.get_by_id(created.id) is not None

    def test_update_status(self, consultation_repo):
        consultation_repo.update_status(1, ConsultationStatus.APPROVED)
        c = consultation_repo.get_by_id(1)
        assert c.status == ConsultationStatus.APPROVED


# ── Prescription Repository ───────────────────────────────────────────


class TestInMemoryPrescriptionRepository:
    def test_list_all(self, prescription_repo):
        assert len(prescription_repo.list_all()) >= 1

    def test_get_by_id(self, prescription_repo):
        p = prescription_repo.get_by_id(1)
        assert p is not None
        assert p.diagnosis == "Essential hypertension, controlled"

    def test_get_by_id_unknown(self, prescription_repo):
        assert prescription_repo.get_by_id(999) is None

    def test_create_prescription(self, prescription_repo):
        p = Prescription(
            consultation_id=1,
            doctor_id=1,
            patient_id=1,
            diagnosis="Test diagnosis",
            medications=[
                Medication(
                    name="Aspirin", dosage="100mg", frequency="daily", duration="7 days"
                )
            ],
        )
        created = prescription_repo.create(p)
        assert created.id is not None


# ── Audit Log Repository ──────────────────────────────────────────────


class TestInMemoryAuditLogRepository:
    def test_list_recent(self, audit_repo):
        audit_repo.append(AuditLog(user_id=1, user_role="doctor", action="LOGIN"))
        entries = audit_repo.list_recent()
        assert len(entries) >= 1

    def test_append(self, audit_repo):
        entry = AuditLog(user_id=1, user_role="doctor", action="TEST_ACTION")
        created = audit_repo.append(entry)
        assert created.id is not None
        assert any(e.action == "TEST_ACTION" for e in audit_repo.list_recent())
