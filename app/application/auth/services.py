"""Authentication application services."""

from __future__ import annotations

from app.domain.auth.models import AuthService, LoginRequest, User, StaffCreateRequest
from app.domain.patients.models import PatientCreateRequest

from app.core.security import hash_password
from app.infrastructure.logging import apply_logging_aspect


@apply_logging_aspect("service", "auth")
class AuthApplicationService:
    def __init__(self, auth_service: AuthService) -> None:
        self.auth_service = auth_service

    def register_patient(self, req: PatientCreateRequest) -> User:
        req.password_hash = hash_password(req.password_hash)
        patient = self.auth_service.patient_repository.create(req)
        return patient.to_user()

    def register_staff(self, req: StaffCreateRequest) -> User:
        req.password_hash = hash_password(req.password_hash)
        staff = self.auth_service.staff_repository.create(req)
        return staff.to_user()

    def login(self, payload: LoginRequest) -> User | None:
        return self.auth_service.authenticate(payload.email, payload.password)
