"""Mock authentication service."""

from __future__ import annotations

from app.domain.auth.models import AuthService, Staff, StaffRepository


class MockAuthService(AuthService):
    def __init__(self, staff_repository: StaffRepository) -> None:
        self.staff_repository = staff_repository

    def authenticate(self, email: str, password: str) -> Staff | None:
        if not password:
            return None
        return self.staff_repository.get_by_email(email)

    def get_current_staff(self) -> Staff:
        return self.staff_repository.get_by_email("doctor@example.local") or Staff(
            id=0, first_name="Dr.", last_name="Placeholder", email="doctor@example.local", role="doctor",
        )
