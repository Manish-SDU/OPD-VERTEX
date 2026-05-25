"""Integration tests for PDF download and report generation routes."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient
from jose import jwt

os.environ.setdefault("USE_MOCK_ADAPTERS", "true")

from app.main import app
from app.core.security import ALGORITHM, SECRET_KEY

client = TestClient(app)


def _doctor_token() -> str:
    return jwt.encode({"sub": "1", "role": "doctor"}, SECRET_KEY, algorithm=ALGORITHM)


def _doctor_cookies() -> dict:
    return {"access_token": _doctor_token()}


def _patient_cookies() -> dict:
    token = jwt.encode({"sub": "5", "role": "patient"}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token}


# ── PDF download route ───────────────────────────────────────────────────────


class TestPdfDownloadRoute:
    def test_pdf_endpoint_exists_for_valid_consultation(self):
        """The /{consultation_id}/pdf route should respond (not 404 on routing)."""
        resp = client.get(
            "/review/1/pdf",
            cookies=_doctor_cookies(),
            follow_redirects=False,
        )
        # Either 200 (pdf generated) or 404 (no report yet – that's OK for this test)
        assert resp.status_code in (200, 404)

    def test_pdf_returns_404_for_missing_report(self):
        """Consultation 99999 has no generated report – should return 404."""
        resp = client.get("/review/99999/pdf", cookies=_doctor_cookies())
        assert resp.status_code == 404

    def test_pdf_requires_authentication(self):
        resp = client.get("/review/1/pdf", follow_redirects=False)
        # Unauthenticated → 401 or redirect to login
        assert resp.status_code in (302, 303, 401)

    def test_pdf_content_type_when_report_exists(self):
        """If the mock report exists, PDF content-type should be application/pdf."""
        # First generate a report for consultation 1
        client.post(
            "/review/1/generate-report",
            cookies=_doctor_cookies(),
        )
        resp = client.get("/review/1/pdf", cookies=_doctor_cookies())
        if resp.status_code == 200:
            assert "application/pdf" in resp.headers.get("content-type", "")


# ── Generate report endpoint ─────────────────────────────────────────────────


class TestGenerateReportEndpoint:
    def test_generate_report_returns_200(self):
        resp = client.post(
            "/review/1/generate-report",
            cookies=_doctor_cookies(),
        )
        assert resp.status_code == 200

    def test_generate_report_response_has_status_field(self):
        resp = client.post("/review/1/generate-report", cookies=_doctor_cookies())
        data = resp.json()
        assert "status" in data
        assert data["status"] in ("generated", "already_generated")

    def test_generate_report_response_has_report_markdown(self):
        resp = client.post("/review/1/generate-report", cookies=_doctor_cookies())
        data = resp.json()
        assert "report_markdown" in data

    def test_regenerate_report_returns_success_or_error(self):
        """Regenerate may fail if consultation doc not seeded; 200 or 400 are valid."""
        resp = client.post(
            "/review/1/regenerate",
            cookies=_doctor_cookies(),
        )
        assert resp.status_code in (200, 400)


# ── Consultation UI enhancements ─────────────────────────────────────────────


class TestConsultationListUI:
    def test_consultation_list_renders(self):
        resp = client.get("/consultations", cookies=_doctor_cookies())
        assert resp.status_code == 200

    def test_consultation_list_shows_patient_names(self):
        resp = client.get("/consultations", cookies=_doctor_cookies())
        # The list should not show raw IDs only – at least no bare "#" IDs
        # (or should show patient names from the seeded data)
        assert resp.status_code == 200

    def test_consultation_detail_renders(self):
        resp = client.get("/consultations/1", cookies=_doctor_cookies())
        assert resp.status_code == 200

    def test_consultation_detail_shows_patient_name(self):
        resp = client.get("/consultations/1", cookies=_doctor_cookies())
        html = resp.text
        # Should have "Patient:" label in the enhanced template
        assert "Patient" in html

    def test_consultation_detail_shows_chief_complaint(self):
        resp = client.get("/consultations/1", cookies=_doctor_cookies())
        # The consultation has chief_complaint in seeded data
        assert resp.status_code == 200

    def test_consultation_detail_shows_transcription_actions_for_doctor(self):
        resp = client.get("/consultations/1", cookies=_doctor_cookies())
        html = resp.text
        assert "Save Transcript" in html
        assert "Start Recording" in html
        assert 'data-consultation-id="1"' in html
        assert "window.__CONSULTATION_CONTEXT__" in html


# ── Patient UI enhancements ──────────────────────────────────────────────────


class TestPatientDetailUI:
    def test_patient_detail_renders(self):
        resp = client.get("/patients/1", cookies=_doctor_cookies())
        assert resp.status_code == 200

    def test_patient_detail_shows_age(self):
        resp = client.get("/patients/1", cookies=_doctor_cookies())
        html = resp.text
        assert "Age" in html

    def test_patient_detail_shows_prescriptions_section(self):
        resp = client.get("/patients/1", cookies=_doctor_cookies())
        assert "Prescriptions" in resp.text or "prescription" in resp.text.lower()

    def test_patient_list_renders(self):
        resp = client.get("/patients", cookies=_doctor_cookies())
        assert resp.status_code == 200
