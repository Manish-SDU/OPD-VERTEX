"""Unit tests for the appointment domain, repository, and service."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.exceptions import AppError
from app.domain.appointments.models import (
    AppointmentCreateRequest,
    AppointmentStatus,
)
from app.infrastructure.persistence.in_memory.repositories import (
    InMemoryAppointmentRepository,
)
from app.application.appointments.services import AppointmentApplicationService
from app.infrastructure.persistence.in_memory.repositories import (
    InMemoryConsultationRepository,
)
from app.domain.common.types import utcnow


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def appt_repo():
    return InMemoryAppointmentRepository()


@pytest.fixture
def consultation_repo():
    return InMemoryConsultationRepository()


@pytest.fixture
def appt_svc(appt_repo, consultation_repo):
    return AppointmentApplicationService(
        repository=appt_repo,
        consultation_repository=consultation_repo,
    )


def _future(minutes: int = 60):
    return utcnow() + timedelta(minutes=minutes)


def _req(**kwargs):
    defaults = dict(
        patient_id=1,
        doctor_id=1,
        scheduled_at=_future(),
        duration_minutes=30,
        reason="Routine check-up",
    )
    defaults.update(kwargs)
    return AppointmentCreateRequest(**defaults)


# ── AppointmentStatus enum ────────────────────────────────────────────────


class TestAppointmentStatus:
    def test_all_statuses(self):
        expected = {"pending", "confirmed", "cancelled", "completed", "no_show"}
        assert {s.value for s in AppointmentStatus} == expected


# ── InMemoryAppointmentRepository ─────────────────────────────────────────


class TestInMemoryAppointmentRepository:
    def test_seeded_appointments_exist(self, appt_repo):
        appointments = appt_repo.list_all()
        assert len(appointments) >= 2

    def test_list_all_ordered_confirmed_first(self, appt_repo):
        appointments = appt_repo.list_all()
        statuses = [a.status for a in appointments]
        # confirmed should come before pending
        if (
            AppointmentStatus.CONFIRMED in statuses
            and AppointmentStatus.PENDING in statuses
        ):
            assert statuses.index(AppointmentStatus.CONFIRMED) < statuses.index(
                AppointmentStatus.PENDING
            )

    def test_get_by_id_returns_appointment(self, appt_repo):
        a = appt_repo.get_by_id(1)
        assert a is not None
        assert a.id == 1

    def test_get_by_id_returns_none_for_unknown(self, appt_repo):
        assert appt_repo.get_by_id(9999) is None

    def test_list_by_patient(self, appt_repo):
        results = appt_repo.list_by_patient(1)
        assert all(a.patient_id == 1 for a in results)

    def test_list_by_patient_returns_empty_for_unknown(self, appt_repo):
        assert appt_repo.list_by_patient(9999) == []

    def test_list_by_doctor(self, appt_repo):
        results = appt_repo.list_by_doctor(1)
        assert all(a.doctor_id == 1 for a in results)

    def test_create_assigns_id(self, appt_repo):
        req = _req(patient_id=5, doctor_id=1, scheduled_at=_future(120))
        a = appt_repo.create(req)
        assert a.id is not None
        assert a.status == AppointmentStatus.PENDING

    def test_create_increments_id(self, appt_repo):
        a1 = appt_repo.create(_req(scheduled_at=_future(100)))
        a2 = appt_repo.create(_req(scheduled_at=_future(200)))
        assert a2.id > a1.id  # type: ignore[operator]

    def test_create_persists(self, appt_repo):
        req = _req(patient_id=99, scheduled_at=_future(300))
        a = appt_repo.create(req)
        assert appt_repo.get_by_id(a.id) is not None  # type: ignore[arg-type]

    def test_update_status(self, appt_repo):
        appt_repo.update_status(1, AppointmentStatus.CONFIRMED)
        a = appt_repo.get_by_id(1)
        assert a.status == AppointmentStatus.CONFIRMED

    def test_cancel(self, appt_repo):
        appt_repo.cancel(2)
        a = appt_repo.get_by_id(2)
        assert a.status == AppointmentStatus.CANCELLED

    def test_link_consultation(self, appt_repo):
        appt_repo.link_consultation(1, 42)
        a = appt_repo.get_by_id(1)
        assert a.consultation_id == 42

    def test_update_status_returns_none_for_unknown(self, appt_repo):
        result = appt_repo.update_status(9999, AppointmentStatus.CONFIRMED)
        assert result is None

    def test_cancel_returns_none_for_unknown(self, appt_repo):
        result = appt_repo.cancel(9999)
        assert result is None


# ── AppointmentApplicationService ─────────────────────────────────────────


class TestAppointmentApplicationService:
    def test_list_appointments_all_for_admin(self, appt_svc):
        user = {"role": "admin", "sub": "2"}
        result = appt_svc.list_appointments(current_user=user)
        assert len(result) >= 2

    def test_list_appointments_filtered_for_patient(self, appt_svc):
        user = {"role": "patient", "sub": "1"}
        result = appt_svc.list_appointments(current_user=user)
        assert all(a.patient_id == 1 for a in result)

    def test_list_appointments_filtered_for_doctor(self, appt_svc):
        user = {"role": "doctor", "sub": "1"}
        result = appt_svc.list_appointments(current_user=user)
        assert all(a.doctor_id == 1 for a in result)

    def test_create_appointment(self, appt_svc):
        req = _req(patient_id=5, scheduled_at=_future(90))
        a = appt_svc.create_appointment(req)
        assert a.id is not None
        assert a.status == AppointmentStatus.PENDING

    def test_create_rejects_zero_duration(self, appt_svc):
        req = _req(duration_minutes=0)
        with pytest.raises(AppError):
            appt_svc.create_appointment(req)

    def test_create_rejects_empty_reason(self, appt_svc):
        req = _req(reason="   ")
        with pytest.raises(AppError):
            appt_svc.create_appointment(req)

    def test_create_prevents_double_booking_exact_time(self, appt_svc):
        slot = _future(400)
        appt_svc.create_appointment(_req(doctor_id=1, scheduled_at=slot))
        with pytest.raises(AppError):
            appt_svc.create_appointment(_req(doctor_id=1, scheduled_at=slot))

    def test_get_appointment(self, appt_svc):
        a = appt_svc.get_appointment(1)
        assert a is not None
        assert a.id == 1

    def test_get_appointment_returns_none_for_unknown(self, appt_svc):
        assert appt_svc.get_appointment(9999) is None

    def test_confirm_appointment(self, appt_svc):
        # seed appt 2 is pending
        result = appt_svc.confirm_appointment(2)
        assert result.status == AppointmentStatus.CONFIRMED

    def test_confirm_raises_for_cancelled(self, appt_svc):
        appt_svc.cancel_appointment(2)
        with pytest.raises(AppError):
            appt_svc.confirm_appointment(2)

    def test_cancel_appointment(self, appt_svc):
        # create a fresh pending appointment
        req = _req(scheduled_at=_future(500))
        a = appt_svc.create_appointment(req)
        result = appt_svc.cancel_appointment(a.id)  # type: ignore[arg-type]
        assert result.status == AppointmentStatus.CANCELLED

    def test_cancel_raises_for_completed(self, appt_svc):
        req = _req(scheduled_at=_future(600))
        a = appt_svc.create_appointment(req)
        appt_svc.complete_appointment(a.id)  # type: ignore[arg-type]
        with pytest.raises(AppError):
            appt_svc.cancel_appointment(a.id)  # type: ignore[arg-type]

    def test_cancel_raises_for_already_cancelled(self, appt_svc):
        req = _req(scheduled_at=_future(700))
        a = appt_svc.create_appointment(req)
        appt_svc.cancel_appointment(a.id)  # type: ignore[arg-type]
        with pytest.raises(AppError):
            appt_svc.cancel_appointment(a.id)  # type: ignore[arg-type]

    def test_complete_appointment(self, appt_svc):
        req = _req(scheduled_at=_future(800))
        a = appt_svc.create_appointment(req)
        result = appt_svc.complete_appointment(a.id)  # type: ignore[arg-type]
        assert result.status == AppointmentStatus.COMPLETED

    def test_complete_raises_for_cancelled(self, appt_svc):
        req = _req(scheduled_at=_future(900))
        a = appt_svc.create_appointment(req)
        appt_svc.cancel_appointment(a.id)  # type: ignore[arg-type]
        with pytest.raises(AppError):
            appt_svc.complete_appointment(a.id)  # type: ignore[arg-type]

    def test_start_consultation_from_appointment(self, appt_svc, appt_repo):
        req = _req(patient_id=1, doctor_id=1, scheduled_at=_future(1000))
        a = appt_svc.create_appointment(req)
        user = {"role": "doctor", "sub": "1"}
        updated_appt, consultation = appt_svc.start_consultation_from_appointment(
            a.id,
            current_user=user,  # type: ignore[arg-type]
        )
        assert consultation.id is not None
        assert updated_appt.consultation_id == consultation.id
        assert updated_appt.status == AppointmentStatus.COMPLETED

    def test_start_consultation_returns_existing_linked_consultation(self, appt_svc):
        req = _req(patient_id=1, doctor_id=1, scheduled_at=_future(1010))
        a = appt_svc.create_appointment(req)
        user = {"role": "doctor", "sub": "1"}

        first_appt, first_consultation = appt_svc.start_consultation_from_appointment(
            a.id,
            current_user=user,  # type: ignore[arg-type]
        )
        second_appt, second_consultation = appt_svc.start_consultation_from_appointment(
            a.id,
            current_user=user,  # type: ignore[arg-type]
        )

        assert first_appt.consultation_id == second_appt.consultation_id
        assert first_consultation.id == second_consultation.id

    def test_start_consultation_raises_for_cancelled(self, appt_svc):
        req = _req(scheduled_at=_future(1100))
        a = appt_svc.create_appointment(req)
        appt_svc.cancel_appointment(a.id)  # type: ignore[arg-type]
        user = {"role": "doctor", "sub": "1"}
        with pytest.raises(AppError):
            appt_svc.start_consultation_from_appointment(a.id, current_user=user)  # type: ignore[arg-type]

    def test_list_upcoming_excludes_past(self, appt_svc):
        past_slot = utcnow() - timedelta(hours=2)
        req = AppointmentCreateRequest(
            patient_id=1,
            doctor_id=1,
            scheduled_at=past_slot,
            duration_minutes=30,
            reason="Past appointment",
        )
        appt_svc.create_appointment(req)
        upcoming = appt_svc.list_upcoming()
        assert all(a.scheduled_at >= utcnow() - timedelta(seconds=5) for a in upcoming)
