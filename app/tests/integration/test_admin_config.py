"""Integration tests for admin configuration management."""

from __future__ import annotations

from fastapi.testclient import TestClient
from jose import jwt

from app.api.deps import (
    _in_memory_audit_repo,
    _in_memory_email_repo,
    _in_memory_prompt_repo,
)
from app.core.security import ALGORITHM, SECRET_KEY
from app.main import app

client = TestClient(app)


def _cookies(user_id: str = "2", role: str = "admin") -> dict[str, str]:
    token = jwt.encode({"sub": user_id, "role": role}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token}


def _reset_admin_repos() -> None:
    _in_memory_prompt_repo.cache_clear()
    _in_memory_email_repo.cache_clear()
    _in_memory_audit_repo.cache_clear()


class TestAdminConfiguration:
    def setup_method(self):
        _reset_admin_repos()

    def teardown_method(self):
        _reset_admin_repos()

    def test_admin_config_page_renders_editors_and_audit(self):
        response = client.get("/admin/config", cookies=_cookies())

        assert response.status_code == 200
        assert "Admin Configuration" in response.text
        assert "Save prompt" in response.text
        assert "Save template" in response.text
        assert "Audit Trail" in response.text

    def test_non_admin_cannot_open_admin_config(self):
        response = client.get(
            "/admin/config", cookies=_cookies(user_id="1", role="doctor")
        )

        assert response.status_code == 403

    def test_admin_can_update_prompt_and_audit_is_visible(self):
        cookies = _cookies()
        response = client.post(
            "/admin/prompts/transcript_normalization_v1",
            cookies=cookies,
            data={
                "prompt_name": "Transcript Normalization Updated",
                "model_target": "qwen3:8b",
                "temperature": "0.1",
                "max_tokens": "1500",
                "system_prompt": "Return normalized transcript JSON only.",
                "user_prompt_template": "Consultation {consultation_id}: {transcript_text}",
            },
            follow_redirects=False,
        )
        page = client.get(response.headers["location"], cookies=cookies)

        assert response.status_code == 303
        assert page.status_code == 200
        assert "Transcript Normalization Updated" in page.text
        assert "ADMIN_PROMPT_UPDATED" in page.text
        assert "Prompt saved and audit entry recorded." in page.text

    def test_admin_can_update_email_template_and_audit_is_visible(self):
        cookies = _cookies()
        response = client.post(
            "/admin/email-templates/prescription_delivery_v1",
            cookies=cookies,
            data={
                "template_name": "Prescription Email Updated",
                "subject_template": "Prescription from Dr. {{doctor_name}}",
                "body_template": "Hello {{patient_name}}, your prescription is attached.",
                "placeholders": "doctor_name, patient_name",
                "from_email": "clinic@example.local",
                "reply_to": "reply@example.local",
            },
            follow_redirects=False,
        )
        page = client.get(response.headers["location"], cookies=cookies)

        assert response.status_code == 303
        assert page.status_code == 200
        assert "Prescription Email Updated" in page.text
        assert "ADMIN_EMAIL_TEMPLATE_UPDATED" in page.text
        assert "Email template saved and audit entry recorded." in page.text
