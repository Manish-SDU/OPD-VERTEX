"""Patient application services."""

from __future__ import annotations

from app.domain.patients.models import Patient, PatientCreateRequest, PatientRepository
from app.infrastructure.logging import apply_logging_aspect


@apply_logging_aspect("service", "patients")
class PatientApplicationService:
    def __init__(self, repository: PatientRepository) -> None:
        self.repository = repository

    def list_patients(self) -> list[Patient]:
        return self.repository.list_all()

    def get_patient(self, patient_id: str) -> Patient | None:
        return self.repository.get_by_id(patient_id)

    def create_patient(self, payload: PatientCreateRequest) -> Patient:
        return self.repository.create(payload)
