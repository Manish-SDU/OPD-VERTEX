"""Authentication application services."""

from __future__ import annotations

from app.domain.auth.models import AuthService, LoginRequest, Staff


class AuthApplicationService:
    def __init__(self, auth_service: AuthService) -> None:
        self.auth_service = auth_service

    def login(self, payload: LoginRequest) -> Staff | None:
        return self.auth_service.authenticate(payload.username, payload.password)
