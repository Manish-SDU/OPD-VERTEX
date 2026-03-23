"""Mock authentication service."""

from __future__ import annotations

from typing import Optional

from bcrypt import checkpw

from app.domain.auth.models import AuthService, StaffRepository, User
from app.domain.patients.models import PatientRepository
from app.infrastructure.logging import apply_logging_aspect


@apply_logging_aspect("infrastructure", "auth", exclude=frozenset({"_verify_password"}))
class MockAuthService(AuthService):
    def __init__(
        self,
        staff_repository: StaffRepository,
        patient_repository: PatientRepository,
    ) -> None:
        self.staff_repository = staff_repository
        self.patient_repository = patient_repository

        self._current_user: Optional[User] = None

    def _verify_password(self, plain: str, hashed: str) -> bool:
        if not hashed:
            return False
        try:
            return checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    def authenticate_staff(self, email: str, password: str) -> User | None:
        staff = self.staff_repository.get_by_email(email)
        if not staff or not staff.is_active:
            return None
        if not self._verify_password(password, staff.password_hash):
            return None
        user = staff.to_user()
        self._current_user = user
        return user

    def authenticate_patient(self, email: str, password: str) -> User | None:
        patient = self.patient_repository.get_by_email(email)
        if not patient or not patient.is_active:
            return None
        if not self._verify_password(password, patient.password_hash):
            return None
        user = patient.to_user()
        self._current_user = user
        return user

    def authenticate(self, email: str, password: str) -> User | None:
        user = self.authenticate_staff(email, password)
        if user:
            return user
        return self.authenticate_patient(email, password)

    def get_current_user(self) -> User | None:
        return self._current_user
