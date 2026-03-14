"""Authentication application services."""

from __future__ import annotations

from app.domain.auth.models import AuthService, LoginRequest, User


class AuthApplicationService:
    def __init__(self, auth_service: AuthService) -> None:
        self.auth_service = auth_service

    def login_staff(self, payload: LoginRequest) -> User | None:
        """Login specifically as staff (doctor/admin)."""
        return self.auth_service.authenticate_staff(payload.email, payload.password)

    def login_patient(self, payload: LoginRequest) -> User | None:
        """Login specifically as patient."""
        return self.auth_service.authenticate_patient(payload.email, payload.password)
