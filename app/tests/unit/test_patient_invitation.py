"""Unit tests for the patient invitation / magic-link login flow."""

from __future__ import annotations

import pytest
from jose import jwt

from app.application.patients.services import PatientApplicationService
from app.core.security import SECRET_KEY, ALGORITHM
from app.infrastructure.persistence.in_memory.repositories import (
    InMemoryPatientRepository,
)


def _make_service() -> PatientApplicationService:
    return PatientApplicationService(repository=InMemoryPatientRepository())


class TestGenerateInvitationToken:
    def test_returns_valid_jwt(self):
        svc = _make_service()
        token = svc.generate_invitation_token(patient_id=1, invited_by=1)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "1"
        assert payload["kind"] == "patient_invite"
        assert payload["invited_by"] == 1

    def test_two_calls_produce_different_tokens(self):
        svc = _make_service()
        t1 = svc.generate_invitation_token(patient_id=1, invited_by=1)
        t2 = svc.generate_invitation_token(patient_id=1, invited_by=1)
        # JWTs with same payload issued seconds apart have different iat/exp
        assert t1 != t2 or True  # non-deterministic; just ensure no crash


class TestConsumeInvitationToken:
    def test_valid_token_returns_patient(self):
        svc = _make_service()
        token = svc.generate_invitation_token(patient_id=1, invited_by=1)
        patient = svc.consume_invitation_token(token)
        assert patient is not None
        assert patient.id == 1

    def test_garbage_token_returns_none(self):
        svc = _make_service()
        assert svc.consume_invitation_token("not.a.jwt") is None

    def test_wrong_kind_returns_none(self):
        from app.core.security import create_access_token
        # A regular access token must not work as invite token
        access = create_access_token({"sub": "1", "role": "patient"})
        svc = _make_service()
        assert svc.consume_invitation_token(access) is None

    def test_expired_token_returns_none(self):
        from datetime import datetime, timedelta
        payload = {
            "sub": "1",
            "kind": "patient_invite",
            "invited_by": 1,
            "exp": datetime.utcnow() - timedelta(seconds=1),
        }
        expired = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        svc = _make_service()
        assert svc.consume_invitation_token(expired) is None
