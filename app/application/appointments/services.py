"""Appointment application service."""

from __future__ import annotations

from datetime import datetime

from app.core.exceptions import AppError
from app.domain.appointments.models import (
    Appointment,
    AppointmentCreateRequest,
    AppointmentRepository,
    AppointmentStatus,
)
from app.domain.consultations.models import (
    Consultation,
    ConsultationRepository,
    ConsultationStatus,
)
from app.domain.common.types import utcnow
from app.infrastructure.logging import apply_logging_aspect


def _naive(dt: datetime) -> datetime:
    """Strip tzinfo so naive and aware datetimes can be compared safely."""
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


@apply_logging_aspect("service", "appointments")
class AppointmentApplicationService:
    def __init__(
        self,
        repository: AppointmentRepository,
        consultation_repository: ConsultationRepository,
    ) -> None:
        self.repository = repository
        self.consultation_repository = consultation_repository

    # ── Queries ────────────────────────────────────────────────────────

    def list_appointments(self, current_user: dict | None = None) -> list[Appointment]:
        if current_user is None:
            return self.repository.list_all()
        role = current_user.get("role")
        user_id = int(current_user.get("sub", 0))
        if role == "patient":
            return self.repository.list_by_patient(user_id)
        if role == "doctor":
            return self.repository.list_by_doctor(user_id)
        return self.repository.list_all()

    def list_by_patient(self, patient_id: int) -> list[Appointment]:
        return self.repository.list_by_patient(patient_id)

    def list_by_doctor(self, doctor_id: int) -> list[Appointment]:
        return self.repository.list_by_doctor(doctor_id)

    def get_appointment(self, appointment_id: int) -> Appointment | None:
        return self.repository.get_by_id(appointment_id)

    def list_upcoming(self, current_user: dict | None = None) -> list[Appointment]:
        """Return pending/confirmed appointments ordered by priority queue rules."""
        now = datetime.now()  # always naive — no tz coercion possible
        appointments = self.list_appointments(current_user)
        return [
            a
            for a in appointments
            if a.status in (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)
            and a.scheduled_at.replace(tzinfo=None) >= now
        ]

    def list_today_queue(self, current_user: dict | None = None) -> list[Appointment]:
        """Return today's pending/confirmed appointments."""
        today = utcnow().date()
        upcoming = self.list_upcoming(current_user)
        return [a for a in upcoming if a.scheduled_at.date() == today]

    # ── Commands ───────────────────────────────────────────────────────

    def create_appointment(self, req: AppointmentCreateRequest) -> Appointment:
        if req.duration_minutes <= 0:
            raise AppError("duration_minutes must be positive")
        if not req.reason or not req.reason.strip():
            raise AppError("reason must not be empty")

        # Prevent exact double-booking for the same doctor at the same time
        existing = self.repository.list_by_doctor(req.doctor_id)
        for appt in existing:
            if appt.status not in (
                AppointmentStatus.CANCELLED,
                AppointmentStatus.NO_SHOW,
            ) and _naive(appt.scheduled_at) == _naive(req.scheduled_at):
                raise AppError(
                    "Doctor already has an appointment at this exact time. "
                    "Please choose a different slot."
                )

        return self.repository.create(req)

    def confirm_appointment(self, appointment_id: int) -> Appointment:
        appointment = self._get_or_raise(appointment_id)
        if appointment.status in (
            AppointmentStatus.CANCELLED,
            AppointmentStatus.COMPLETED,
        ):
            raise AppError(
                f"Cannot confirm an appointment with status '{appointment.status}'."
            )
        result = self.repository.update_status(
            appointment_id, AppointmentStatus.CONFIRMED
        )
        return result  # type: ignore[return-value]

    def cancel_appointment(self, appointment_id: int) -> Appointment:
        appointment = self._get_or_raise(appointment_id)
        if appointment.status == AppointmentStatus.COMPLETED:
            raise AppError("Cannot cancel a completed appointment.")
        if appointment.status == AppointmentStatus.CANCELLED:
            raise AppError("Appointment is already cancelled.")
        result = self.repository.cancel(appointment_id)
        return result  # type: ignore[return-value]

    def complete_appointment(self, appointment_id: int) -> Appointment:
        appointment = self._get_or_raise(appointment_id)
        if appointment.status == AppointmentStatus.CANCELLED:
            raise AppError("Cannot complete a cancelled appointment.")
        if appointment.status == AppointmentStatus.NO_SHOW:
            raise AppError("Cannot complete a no-show appointment.")
        result = self.repository.update_status(
            appointment_id, AppointmentStatus.COMPLETED
        )
        return result  # type: ignore[return-value]

    def mark_no_show(self, appointment_id: int) -> Appointment:
        appointment = self._get_or_raise(appointment_id)
        if appointment.status in (
            AppointmentStatus.COMPLETED,
            AppointmentStatus.CANCELLED,
        ):
            raise AppError(
                f"Cannot mark as no-show an appointment with status '{appointment.status}'."
            )
        result = self.repository.update_status(
            appointment_id, AppointmentStatus.NO_SHOW
        )
        return result  # type: ignore[return-value]

    def start_consultation_from_appointment(
        self, appointment_id: int, current_user: dict
    ) -> tuple[Appointment, Consultation]:
        """Convert an appointment into a live consultation.

        Creates a new Consultation row linked to this appointment,
        marks the appointment as completed, and stores the consultation_id.
        Only doctor/admin may call this.
        """
        appointment = self._get_or_raise(appointment_id)
        if appointment.consultation_id is not None:
            consultation = self.consultation_repository.get_by_id(
                appointment.consultation_id
            )
            if consultation is None:
                raise AppError(
                    "This appointment is linked to a consultation that could not be found."
                )
            return appointment, consultation

        if appointment.status in (
            AppointmentStatus.CANCELLED,
            AppointmentStatus.NO_SHOW,
            AppointmentStatus.COMPLETED,
        ):
            raise AppError(
                f"Cannot start a consultation from an appointment with status '{appointment.status}'."
            )

        doctor_id = int(current_user.get("sub", 0))
        consultation = Consultation(
            doctor_id=doctor_id,
            patient_id=appointment.patient_id,
            chief_complaint=appointment.reason,
            status=ConsultationStatus.RECORDING,
            started_at=utcnow(),
        )
        consultation = self.consultation_repository.create(consultation)

        self.repository.link_consultation(appointment_id, consultation.id)  # type: ignore[arg-type]
        self.repository.update_status(appointment_id, AppointmentStatus.COMPLETED)

        updated_appointment = self.repository.get_by_id(appointment_id)
        return updated_appointment, consultation  # type: ignore[return-value]

    # ── Private helpers ────────────────────────────────────────────────

    def _get_or_raise(self, appointment_id: int) -> Appointment:
        appointment = self.repository.get_by_id(appointment_id)
        if appointment is None:
            raise AppError(f"Appointment {appointment_id} not found.")
        return appointment
