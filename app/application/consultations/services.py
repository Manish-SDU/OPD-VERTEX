"""Consultation application services."""

from __future__ import annotations

from app.domain.common.types import utcnow
from app.domain.consultations.models import (
    Consultation,
    ConsultationCreateRequest,
    ConsultationRepository,
    ConsultationStatus,
)


class ConsultationApplicationService:
    def __init__(self, repository: ConsultationRepository) -> None:
        self.repository = repository

    def list_consultations(self) -> list[Consultation]:
        return self.repository.list_all()

    def get_consultation(self, consultation_id: int) -> Consultation | None:
        return self.repository.get_by_id(consultation_id)

    def create_consultation(self, payload: ConsultationCreateRequest, doctor_id: int) -> Consultation:
        consultation = Consultation(
            doctor_id=doctor_id,
            patient_id=payload.patient_id,
            status=ConsultationStatus.RECORDING,
            started_at=utcnow(),
        )
        return self.repository.create(consultation)
