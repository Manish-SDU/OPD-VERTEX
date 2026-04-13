"""Authentication application services."""

from __future__ import annotations

from app.domain.auth.models import AuthService, LoginRequest, User

from app.infrastructure.logging import apply_logging_aspect


@apply_logging_aspect("service", "auth")
class AuthApplicationService:
    def __init__(self, auth_service: AuthService) -> None:
        self.auth_service = auth_service

    def login(self, payload: LoginRequest) -> User | None:
        return self.auth_service.authenticate(payload.email, payload.password)
