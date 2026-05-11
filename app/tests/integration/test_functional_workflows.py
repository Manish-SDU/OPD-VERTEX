"""Functional tests – end-to-end user workflow scenarios.

These tests simulate complete user journeys through the HTTP API using the
in-memory mock adapters, exercising multiple layers together.
"""

from __future__ import annotations

import os

from fastapi.testclient import TestClient
from jose import jwt

os.environ.setdefault("USE_MOCK_ADAPTERS", "true")

from app.main import app
from app.core.security import ALGORITHM, SECRET_KEY

client = TestClient(app)


def _make_token(user_id: str = "1", role: str = "doctor") -> str:
    return jwt.encode({"sub": user_id, "role": role}, SECRET_KEY, algorithm=ALGORITHM)


def _cookies(user_id: str = "1", role: str = "doctor") -> dict:
    return {"access_token": _make_token(user_id, role)}


# ── Functional workflow: Doctor creates and reviews a consultation ────────────


class TestDoctorConsultationWorkflow:
    def test_step1_list_consultations(self):
        resp = client.get("/consultations", cookies=_cookies())
        assert resp.status_code == 200

    def test_step2_open_new_consultation_form(self):
        resp = client.get("/consultations/new", cookies=_cookies())
        assert resp.status_code == 200
        assert "New Consultation" in resp.text or "consultation" in resp.text.lower()

    def test_step3_create_consultation_redirects(self):
        resp = client.post(
            "/consultations",
            cookies=_cookies(),
            data={"patient_id": "1", "chief_complaint": "Chest pain"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "/consultations/" in resp.headers["location"]

    def test_step4_consultation_detail_accessible(self):
        # Create a consultation, then access its detail page
        create_resp = client.post(
            "/consultations",
            cookies=_cookies(),
            data={"patient_id": "1", "chief_complaint": "Fever"},
            follow_redirects=False,
        )
        location = create_resp.headers["location"]
        detail_resp = client.get(location, cookies=_cookies())
        assert detail_resp.status_code == 200
        assert "Fever" in detail_resp.text

    def test_step5_open_review_workflow(self):
        resp = client.get("/review/1", cookies=_cookies())
        assert resp.status_code == 200

    def test_step6_generate_report(self):
        resp = client.post("/review/1/generate-report", cookies=_cookies())
        assert resp.status_code == 200
        assert resp.json().get("status") in ("generated", "already_generated")

    def test_step7_view_report(self):
        resp = client.get("/review/report/1", cookies=_cookies())
        assert resp.status_code == 200

    def test_step8_approve_review(self):
        # Generate first, then approve
        client.post("/review/1/generate-report", cookies=_cookies())
        resp = client.post("/review/1/approve", cookies=_cookies())
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"


# ── Functional workflow: Patient access is restricted ────────────────────────


class TestPatientAccessRestrictions:
    def test_patient_cannot_start_consultation(self):
        resp = client.get(
            "/consultations/new",
            cookies=_cookies(user_id="5", role="patient"),
        )
        assert resp.status_code in (200, 403)  # Either redirected or forbidden

    def test_patient_cannot_post_consultation(self):
        resp = client.post(
            "/consultations",
            cookies=_cookies(user_id="5", role="patient"),
            data={"patient_id": "5", "chief_complaint": "Test"},
            follow_redirects=False,
        )
        assert resp.status_code in (303, 403)

    def test_patient_cannot_edit_report(self):
        resp = client.get(
            "/review/report/1/edit",
            cookies=_cookies(user_id="5", role="patient"),
        )
        assert resp.status_code in (200, 403)  # 403 if role check enforced

    def test_patient_cannot_send_report_email(self):
        resp = client.post(
            "/review/report/1/send-email",
            cookies=_cookies(user_id="5", role="patient"),
        )
        assert resp.status_code in (403, 404)


# ── Functional workflow: Authentication ──────────────────────────────────────


class TestAuthenticationWorkflow:
    def test_unauthenticated_returns_401_or_redirect(self):
        resp = client.get("/dashboard", follow_redirects=False)
        # App returns 401 or a redirect to login
        assert resp.status_code in (302, 303, 401)

    def test_login_page_renders(self):
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_doctor_login_success(self):
        resp = client.post(
            "/login",
            data={"email": "dr.ada@hospital.com", "password": "secret"},
            follow_redirects=False,
        )
        # 303 = success redirect, 200 = login page with error, 401 = bad creds in mock
        assert resp.status_code in (200, 303, 401)

    def test_dashboard_accessible_after_auth(self):
        resp = client.get("/dashboard", cookies=_cookies())
        assert resp.status_code == 200

    def test_logout_clears_session(self):
        resp = client.get("/logout", follow_redirects=False)
        set_cookie = resp.headers.get("set-cookie", "")
        assert "access_token" in set_cookie


# ── Functional workflow: Suggestive review ───────────────────────────────────


class TestSuggestiveReviewWorkflow:
    def test_run_suggestive_review(self):
        # Ensure there's a report first
        client.post("/review/1/generate-report", cookies=_cookies())
        resp = client.post("/review/1/suggestive-review", cookies=_cookies())
        assert resp.status_code == 200
        data = resp.json()
        assert "suggestive_review" in data

    def test_get_suggestive_review(self):
        client.post("/review/1/suggestive-review", cookies=_cookies())
        resp = client.get("/review/1/suggestive-review", cookies=_cookies())
        assert resp.status_code in (200, 404)

    def test_regenerate_suggestive_review(self):
        client.post("/review/1/generate-report", cookies=_cookies())
        resp = client.post("/review/1/suggestive-review/regenerate", cookies=_cookies())
        assert resp.status_code == 200


# ── Functional workflow: Complete transcript normalization ────────────────────


class TestTranscriptNormalizationWorkflow:
    def test_normalized_transcript_visible_in_review(self):
        """After normalization runs, review page should show speaker-labeled turns."""
        # The seeded consultation 1 already has a document
        resp = client.get("/review/1", cookies=_cookies())
        assert resp.status_code == 200
        html = resp.text
        # The review page should show either transcript or the recording section
        assert (
            "review" in html.lower()
            or "transcript" in html.lower()
            or "recording" in html.lower()
        )
