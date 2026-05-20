"""RBAC permission tests.

Verifies that clinical actions are restricted to doctors,
operational actions allow doctor+admin, and admin cannot
perform clinical approvals.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.core.security import ALGORITHM, SECRET_KEY

client = TestClient(app, follow_redirects=False)


# ── Token helpers ─────────────────────────────────────────────────────────


def _token(role: str, sub: str = "1") -> dict[str, str]:
    return {
        "access_token": jwt.encode(
            {"sub": sub, "role": role}, SECRET_KEY, algorithm=ALGORITHM
        )
    }


def _doctor_cookie(sub: str = "1") -> dict[str, str]:
    return _token("doctor", sub)


def _admin_cookie(sub: str = "99") -> dict[str, str]:
    return _token("admin", sub)


def _patient_cookie(sub: str = "10") -> dict[str, str]:
    return _token("patient", sub)


# ── Clinical routes: doctor-only ──────────────────────────────────────────


class TestClinicalDoctorOnly:
    """Admin and patient must receive 403 on clinical endpoints."""

    def test_admin_cannot_approve_prescription(self):
        response = client.post("/review/1/approve", cookies=_admin_cookie())
        assert response.status_code == 403

    def test_admin_cannot_reject_review(self):
        response = client.post("/review/1/reject", cookies=_admin_cookie())
        assert response.status_code == 403

    def test_admin_cannot_generate_report(self):
        response = client.post("/review/4101/generate-report", cookies=_admin_cookie())
        assert response.status_code == 403

    def test_admin_cannot_regenerate_report(self):
        response = client.post("/review/4101/regenerate", cookies=_admin_cookie())
        assert response.status_code == 403

    def test_admin_cannot_run_suggestive_review(self):
        response = client.post(
            "/review/4101/suggestive-review", cookies=_admin_cookie()
        )
        assert response.status_code == 403

    def test_admin_cannot_regenerate_suggestive_review(self):
        response = client.post(
            "/review/4101/suggestive-review/regenerate", cookies=_admin_cookie()
        )
        assert response.status_code == 403

    def test_admin_cannot_edit_report(self):
        response = client.get("/review/report/4101/edit", cookies=_admin_cookie())
        assert response.status_code == 403

    def test_patient_cannot_approve_prescription(self):
        response = client.post("/review/1/approve", cookies=_patient_cookie())
        assert response.status_code == 403

    def test_patient_cannot_generate_report(self):
        response = client.post(
            "/review/4101/generate-report", cookies=_patient_cookie()
        )
        assert response.status_code == 403

    def test_doctor_can_approve_prescription(self):
        response = client.post("/review/1/approve", cookies=_doctor_cookie())
        assert response.status_code == 200
        assert response.json()["status"] == "approved"

    def test_doctor_can_generate_report(self):
        response = client.post("/review/4101/generate-report", cookies=_doctor_cookie())
        assert response.status_code == 200

    def test_doctor_can_edit_report(self):
        response = client.get("/review/report/4101/edit", cookies=_doctor_cookie())
        assert response.status_code == 200


# ── Appointment: start-consultation is doctor-only ────────────────────────


class TestConsultationStartDoctorOnly:
    """Starting a consultation from an appointment is a clinical action."""

    def test_admin_cannot_start_consultation(self):
        # Appointment #1 is seeded in the mock repo
        response = client.post(
            "/appointments/1/start-consultation", cookies=_admin_cookie()
        )
        assert response.status_code == 403

    def test_patient_cannot_start_consultation(self):
        response = client.post(
            "/appointments/1/start-consultation", cookies=_patient_cookie()
        )
        assert response.status_code == 403

    def test_doctor_can_start_consultation(self):
        response = client.post(
            "/appointments/1/start-consultation", cookies=_doctor_cookie()
        )
        # 303 redirect on success, or 409 if already started — both mean the check passed
        assert response.status_code in (303, 409)


# ── Appointment: operational actions allow doctor + admin ─────────────────


class TestOperationalAppointmentActions:
    """Confirm and no-show are operational — both doctor and admin may act."""

    def test_admin_can_confirm_appointment(self):
        response = client.post("/appointments/1/confirm", cookies=_admin_cookie())
        # 303 redirect means access was granted (business logic may raise 409)
        assert response.status_code in (303, 409)

    def test_doctor_can_confirm_appointment(self):
        response = client.post("/appointments/1/confirm", cookies=_doctor_cookie())
        assert response.status_code in (303, 409)

    def test_patient_cannot_confirm_appointment(self):
        response = client.post("/appointments/1/confirm", cookies=_patient_cookie())
        assert response.status_code == 403

    def test_admin_can_mark_no_show(self):
        response = client.post("/appointments/2/no-show", cookies=_admin_cookie())
        assert response.status_code in (303, 409)

    def test_doctor_can_mark_no_show(self):
        response = client.post("/appointments/2/no-show", cookies=_doctor_cookie())
        assert response.status_code in (303, 409)

    def test_patient_cannot_mark_no_show(self):
        response = client.post("/appointments/2/no-show", cookies=_patient_cookie())
        assert response.status_code == 403


# ── Patient data isolation ────────────────────────────────────────────────


class TestPatientDataIsolation:
    """Patients see their own appointments; admins see all."""

    def test_patient_can_view_own_appointment_list(self):
        response = client.get("/appointments", cookies=_patient_cookie())
        assert response.status_code == 200

    def test_admin_can_view_all_appointments(self):
        response = client.get("/appointments", cookies=_admin_cookie())
        assert response.status_code == 200

    def test_unauthenticated_cannot_view_appointments(self):
        response = client.get("/appointments")
        assert response.status_code == 401


# ── Unauthenticated access is blocked everywhere ──────────────────────────


class TestUnauthenticated:
    def test_no_cookie_approve_returns_401(self):
        response = client.post("/review/1/approve")
        assert response.status_code == 401

    def test_no_cookie_generate_returns_401(self):
        response = client.post("/review/4101/generate-report")
        assert response.status_code == 401

    def test_no_cookie_start_consultation_returns_401(self):
        response = client.post("/appointments/1/start-consultation")
        assert response.status_code == 401
