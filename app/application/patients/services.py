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

    def search_patients(self, query: str) -> list[Patient]:
        """Filter patients by name or ID (case-insensitive substring match)."""
        if not query.strip():
            return self.repository.list_all()
        q = query.strip().lower()
        return [
            p
            for p in self.repository.list_all()
            if q in p.first_name.lower()
            or q in p.last_name.lower()
            or q in f"{p.first_name} {p.last_name}".lower()
            or (q.isdigit() and p.id is not None and q in str(p.id))
        ]

    def get_patient(self, patient_id: str) -> Patient | None:
        return self.repository.get_by_id(patient_id)

    def create_patient(self, req: PatientCreateRequest) -> Patient:
        return self.repository.create(req)
