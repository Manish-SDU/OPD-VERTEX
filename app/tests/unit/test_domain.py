"""Unit tests for domain models and types."""

from __future__ import annotations

from datetime import date, timezone

from app.domain.auth.models import Staff, User
from app.domain.common.types import generate_id, utcnow
from app.domain.consultations.models import ConsultationStatus
from app.domain.patients.models import Patient
from app.domain.prescriptions.models import Medication
from app.domain.suggestive_mode.models import (
    RiskLevel,
    SuggestionSeverity,
    SuggestionType,
)


class TestGenerateId:
    def test_has_prefix(self):
        result = generate_id("pat")
        assert result.startswith("pat_")

    def test_unique(self):
        ids = {generate_id("x") for _ in range(100)}
        assert len(ids) == 100


class TestUtcNow:
    def test_returns_utc_aware_datetime(self):
        now = utcnow()
        assert now.tzinfo == timezone.utc


class TestConsultationStatus:
    def test_all_statuses(self):
        expected = {
            "recording",
            "transcribing",
            "processing",
            "review",
            "approved",
            "rejected",
            "cancelled",
        }
        assert {s.value for s in ConsultationStatus} == expected


class TestStaffToUser:
    def test_converts_to_user(self):
        staff = Staff(
            id=1,
            first_name="Ada",
            last_name="Demo",
            email="ada@example.com",
            role="doctor",
        )
        user = staff.to_user()
        assert isinstance(user, User)
        assert user.email == "ada@example.com"
        assert user.role == "doctor"


class TestPatientModel:
    def test_default_role(self):
        p = Patient(
            first_name="A",
            last_name="B",
            date_of_birth=date(2000, 1, 1),
            email="a@b.com",
        )
        assert p.role == "patient"


class TestMedicationModel:
    def test_default_route(self):
        med = Medication(
            name="Aspirin", dosage="100mg", frequency="daily", duration="7 days"
        )
        assert med.route == "oral"


class TestSuggestiveEnums:
    def test_risk_levels(self):
        assert RiskLevel.GREEN.value == "GREEN"
        assert RiskLevel.RED.value == "RED"

    def test_severity_levels(self):
        assert SuggestionSeverity.CRITICAL.value == "CRITICAL"

    def test_suggestion_types(self):
        assert SuggestionType.OMISSION.value == "OMISSION"
        assert SuggestionType.CONTRAINDICATION.value == "CONTRAINDICATION"
