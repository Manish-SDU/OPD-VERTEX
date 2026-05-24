from __future__ import annotations

import os

from fastapi.testclient import TestClient
from jose import jwt

os.environ["USE_MOCK_ADAPTERS"] = "true"
os.environ["DEBUG"] = "false"

from app.core.security import ALGORITHM, SECRET_KEY
from app.main import app

client = TestClient(app)


def _doctor_cookies() -> dict:
    token = jwt.encode({"sub": "1", "role": "doctor"}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token}


class TestManualTranscriptionFlow:
    def test_typed_transcript_can_be_saved_and_used_for_report_generation(self):
        create_response = client.post(
            "/consultations",
            data={"patient_id": 1, "chief_complaint": "Manual transcript test"},
            cookies=_doctor_cookies(),
            follow_redirects=False,
        )
        assert create_response.status_code == 303

        consultation_id = int(
            create_response.headers["location"].rstrip("/").split("/")[-1]
        )

        session_response = client.post(
            "/transcriptions/session/start",
            json={"consultation_id": consultation_id},
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["session_id"]

        inject_response = client.post(
            f"/transcriptions/session/{session_id}/inject-demo",
            json={"text": "Patient reports sore throat for three days and mild fever."},
        )
        assert inject_response.status_code == 200

        save_response = client.post(
            "/transcriptions/save-transcription",
            json={
                "consultation_id": consultation_id,
                "session_id": session_id,
            },
        )
        assert save_response.status_code == 200
        assert (
            save_response.json()["full_text"]
            == "Patient reports sore throat for three days and mild fever."
        )

        report_response = client.post(
            f"/review/{consultation_id}/generate-report",
            cookies=_doctor_cookies(),
        )
        assert report_response.status_code == 200
        assert report_response.json()["consultation_id"] == consultation_id

    def test_empty_transcript_cannot_be_saved(self):
        create_response = client.post(
            "/consultations",
            data={"patient_id": 1, "chief_complaint": "Empty transcript test"},
            cookies=_doctor_cookies(),
            follow_redirects=False,
        )
        assert create_response.status_code == 303

        consultation_id = int(
            create_response.headers["location"].rstrip("/").split("/")[-1]
        )

        session_response = client.post(
            "/transcriptions/session/start",
            json={"consultation_id": consultation_id},
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["session_id"]

        save_response = client.post(
            "/transcriptions/save-transcription",
            json={
                "consultation_id": consultation_id,
                "session_id": session_id,
            },
        )
        assert save_response.status_code == 400
        assert "cannot be saved without a transcript" in save_response.json()["detail"]
