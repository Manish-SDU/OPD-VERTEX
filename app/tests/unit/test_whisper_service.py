from __future__ import annotations

from collections import deque
import importlib
import sys
import types

import numpy as np


class TestWhisperFinalizeSession:
    def test_finalize_session_flushes_residual_audio_before_returning(
        self, monkeypatch
    ):
        stub_module = types.ModuleType("faster_whisper")
        stub_module.WhisperModel = object
        monkeypatch.setitem(sys.modules, "faster_whisper", stub_module)

        whisper_service = importlib.import_module("whisper_api.service")

        session_id = "session-test"
        whisper_service._sessions[session_id] = {
            "consultation_id": 77,
            "buffer": deque([np.array([0.1, -0.1], dtype=np.float32)]),
            "results": [],
            "threads": [],
            "chunk_count": 0,
            "timestamp": 0.0,
            "chunk_duration": 2.0,
            "sample_rate": 16000,
            "chunk_size": 32000,
        }

        def fake_transcribe_chunk(
            active_session_id: str, audio_chunk: np.ndarray
        ) -> None:
            assert active_session_id == session_id
            assert len(audio_chunk) == 2
            whisper_service._sessions[active_session_id]["results"].append(
                "Residual audio captured"
            )

        monkeypatch.setattr(whisper_service, "_transcribe_chunk", fake_transcribe_chunk)

        result = whisper_service.finalize_session(session_id)

        assert result["consultation_id"] == 77
        assert result["full_text"] == "Residual audio captured"
        assert session_id not in whisper_service._sessions
