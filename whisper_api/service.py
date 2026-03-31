"""Whisper API service - wrapper around Faster-Whisper for REST/HTTP access."""

from __future__ import annotations

import os
import threading
import uuid
from collections import deque
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

# Session storage for streaming
_sessions: dict[str, dict] = {}
_lock = threading.Lock()


def init_model(model_size: str = "base", device: str = "cuda"):
    """Initialize Whisper model."""
    models_dir = Path(__file__).parent.parent / "models"
    os.environ['HF_HOME'] = str(models_dir)
    return WhisperModel(model_size, device=device)


# Global model instance
model = None


def start_streaming_session(consultation_id: int, chunk_duration: float = 2.0, sample_rate: int = 16000) -> str:
    """Initialize a streaming session."""
    global _sessions
    session_id = str(uuid.uuid4())
    with _lock:
        _sessions[session_id] = {
            "consultation_id": consultation_id,
            "buffer": deque(),
            "results": [],
            "chunk_count": 0,
            "timestamp": 0.0,
            "chunk_duration": chunk_duration,
            "sample_rate": sample_rate,
            "chunk_size": int(chunk_duration * sample_rate),
        }
    return session_id


def add_audio_chunk(session_id: str, audio_bytes: bytes) -> dict:
    """Add audio chunk and optionally return transcription."""
    global _sessions, model
    with _lock:
        if session_id not in _sessions:
            raise ValueError(f"Session {session_id} not found")

        session = _sessions[session_id]

        audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        session["buffer"].append(audio_data)

        total_samples = sum(len(chunk) for chunk in session["buffer"])

        if total_samples >= session["chunk_size"]:
            audio_chunk = np.concatenate(list(session["buffer"]))
            session["buffer"].clear()

            thread = threading.Thread(
                target=_transcribe_chunk,
                args=(session_id, audio_chunk),
            )
            thread.daemon = True
            thread.start()

            chunk_id = session["chunk_count"]
            session["chunk_count"] += 1

            return {
                "chunk_id": chunk_id,
                "text": "[processing...]",
                "timestamp": session["timestamp"],
                "is_final": False,
            }

    return None


def _transcribe_chunk(session_id: str, audio_chunk: np.ndarray) -> None:
    """Transcribe audio chunk in background thread."""
    global _sessions, model
    try:
        if model is None:
            print(f"[ERROR] Model not initialized for session {session_id}")
            return
            
        import tempfile
        import soundfile as sf

        print(f"[Whisper] Transcribing chunk for session {session_id}: {len(audio_chunk)} samples, duration ~{len(audio_chunk) / 16000:.2f}s")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, audio_chunk, _sessions[session_id]["sample_rate"])
            print(f"[Whisper] Wrote audio to {f.name}, size: {os.path.getsize(f.name)} bytes")

            segments, info = model.transcribe(f.name, language="en")
            text = " ".join([segment.text for segment in segments])
            print(f"[Whisper] Transcribed: '{text}' (detected lang: {info.language})")

            with _lock:
                if session_id in _sessions:
                    _sessions[session_id]["results"].append(text)
                    print(f"[Whisper] Results accumulated: {_sessions[session_id]['results']}")

            # Clean up temp file
            try:
                os.unlink(f.name)
            except:
                pass

    except Exception as e:
        print(f"[ERROR] Transcribing chunk for {session_id}: {e}")
        import traceback
        traceback.print_exc()


def finalize_session(session_id: str) -> dict:
    """End streaming and combine all results."""
    global _sessions
    with _lock:
        if session_id not in _sessions:
            raise ValueError(f"Session {session_id} not found")

        session = _sessions.pop(session_id)
        full_text = " ".join(session["results"])

    return {
        "consultation_id": session["consultation_id"],
        "full_text": full_text,
        "language": "en",
    }


def get_current_text(session_id: str) -> str:
    """Get transcription accumulated so far."""
    global _sessions
    with _lock:
        if session_id not in _sessions:
            return ""
        # Filter out empty/whitespace-only results and join properly
        results = _sessions[session_id]["results"]
        non_empty = [r.strip() for r in results if r and r.strip()]
        combined = " ".join(non_empty)
        return combined
