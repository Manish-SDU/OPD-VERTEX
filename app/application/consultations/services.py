"""Consultation application services."""

from __future__ import annotations

from app.domain.consultations.models import Consultation, ConsultationCreateRequest, ConsultationRepository


class ConsultationApplicationService:
    def __init__(self, repository: ConsultationRepository) -> None:
        self.repository = repository

    def list_consultations(self) -> list[Consultation]:
        return self.repository.list_all()

    def get_consultation(self, consultation_id: str) -> Consultation | None:
        return self.repository.get_by_id(consultation_id)

    def create_consultation(self, payload: ConsultationCreateRequest, clinician_id: str) -> Consultation:
        return self.repository.create(payload, clinician_id)
