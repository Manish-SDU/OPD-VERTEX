"""Patient application services."""

from __future__ import annotations

from app.core.security import create_patient_invite_token, decode_patient_invite_token
from app.domain.patients.models import (
    Patient,
    PatientCreateRequest,
    PatientInvitationTokenRepository,
    PatientRepository,
)
from app.infrastructure.logging import apply_logging_aspect


@apply_logging_aspect("service", "patients")
class PatientApplicationService:
    def __init__(
        self,
        repository: PatientRepository,
        token_repository: PatientInvitationTokenRepository | None = None,
    ) -> None:
        self.repository = repository
        self.token_repository = token_repository  # kept for compat, unused

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

    # ------------------------------------------------------------------ #
    # Invitation link flow — stateless signed JWT, no DB storage needed   #
    # ------------------------------------------------------------------ #

    def generate_invitation_token(self, patient_id: int, invited_by: int) -> str:
        """Return a signed JWT that encodes the patient id and expiry (72 h)."""
        return create_patient_invite_token(patient_id=patient_id, invited_by=invited_by)

    def consume_invitation_token(self, token: str) -> Patient | None:
        """Decode and validate the JWT, then return the patient. None if invalid/expired."""
        payload = decode_patient_invite_token(token)
        if payload is None:
            return None
        patient_id = int(payload["sub"])
        return self.repository.get_by_id(patient_id)
