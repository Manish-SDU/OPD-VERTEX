"""Mock authentication service."""

from __future__ import annotations

from app.domain.auth.models import AuthService, Staff, StaffRepository


class MockAuthService(AuthService):
    def __init__(self, staff_repository: StaffRepository) -> None:
        self.staff_repository = staff_repository

    def authenticate(self, username: str, password: str) -> Staff | None:
        # TODO: replace with proper password verification and session management.
        if not password:
            return None
        return self.staff_repository.get_by_username(username)

    def get_current_staff(self) -> Staff:
        return self.staff_repository.get_by_username("doctor.demo") or Staff(
            id="staff_fallback",
            username="doctor.demo",
            full_name="Dr. Placeholder",
            role="doctor",
        )
