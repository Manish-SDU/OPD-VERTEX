"""Prescription application services."""

from __future__ import annotations

from app.domain.prescriptions.models import Prescription, PrescriptionRepository
from app.infrastructure.logging import apply_logging_aspect


@apply_logging_aspect("service", "prescriptions")
class PrescriptionApplicationService:
    def __init__(self, repository: PrescriptionRepository) -> None:
        self.repository = repository

    def list_prescriptions(self) -> list[Prescription]:
        return self.repository.list_all()

    def get_prescription(self, prescription_id: int) -> Prescription | None:
        return self.repository.get_by_id(prescription_id)
