"""Whisper API service - wrapper around Faster-Whisper for REST/HTTP access."""

from __future__ import annotations

import logging
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
logger = logging.getLogger("opd_vertex.whisper_api.service")


def init_model(model_size: str = "large-v3", device: str = "cuda"):
    """Initialize Whisper model."""
    models_dir = Path(__file__).parent.parent / "models"
    os.environ["HF_HOME"] = str(models_dir)
    return WhisperModel(model_size, device=device)


# Global model instance
model = None


def start_streaming_session(
    consultation_id: int, chunk_duration: float = 2.0, sample_rate: int = 16000
) -> str:
    """Initialize a streaming session."""
    global _sessions
    session_id = str(uuid.uuid4())
    with _lock:
        _sessions[session_id] = {
            "consultation_id": consultation_id,
            "buffer": deque(),
            "results": [],
            "threads": [],
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

        audio_data = (
            np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        )
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
            session["threads"].append(thread)

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
            logger.error("Whisper model not initialized session_id=%s", session_id)
            return

        import tempfile
        import soundfile as sf
        import webrtcvad

        logger.debug(
            "Transcribing audio chunk session_id=%s samples=%s duration_seconds=%.2f",
            session_id,
            len(audio_chunk),
            len(audio_chunk) / 16000,
        )

        # --- Preprocessing: normalize audio ---
        norm_audio = audio_chunk / (np.max(np.abs(audio_chunk)) + 1e-8)

        # --- Preprocessing: remove silence using VAD ---
        vad = webrtcvad.Vad(3)  # Aggressiveness: 0-3
        sample_rate = _sessions[session_id]["sample_rate"]
        frame_duration = 30  # ms
        frame_size = int(sample_rate * frame_duration / 1000)
        voiced_audio = []
        for start in range(0, len(norm_audio), frame_size):
            frame = norm_audio[start : start + frame_size]
            if len(frame) < frame_size:
                break
            # Convert to 16-bit PCM for VAD
            pcm = (frame * 32767).astype(np.int16).tobytes()
            if vad.is_speech(pcm, sample_rate):
                voiced_audio.append(frame)
        if voiced_audio:
            processed_audio = np.concatenate(voiced_audio)
        else:
            processed_audio = norm_audio  # fallback if VAD removes everything

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, processed_audio, sample_rate)
            logger.debug(
                "Prepared temporary audio file session_id=%s bytes=%s",
                session_id,
                os.path.getsize(f.name),
            )

            # --- Decoding: beam search, temperature=0, disable context carryover ---
            segments, info = model.transcribe(
                f.name,
                language="en",
                beam_size=5,  # beam search
                temperature=0.0,
                without_timestamps=False,
                condition_on_previous_text=False,  # disables context carryover
            )
            text = " ".join([segment.text for segment in segments])
            logger.debug(
                "Whisper transcription completed session_id=%s detected_language=%s characters=%s",
                session_id,
                info.language,
                len(text),
            )

            with _lock:
                if session_id in _sessions:
                    _sessions[session_id]["results"].append(text)
                    logger.debug(
                        "Whisper session updated session_id=%s result_count=%s",
                        session_id,
                        len(_sessions[session_id]["results"]),
                    )

            # Clean up temp file
            try:
                os.unlink(f.name)
            except Exception:
                pass

    except Exception:
        logger.exception("Whisper transcription failed session_id=%s", session_id)


def finalize_session(session_id: str) -> dict:
    """End streaming and combine all results."""
    global _sessions

    residual_audio = None
    threads: list[threading.Thread] = []
    with _lock:
        if session_id not in _sessions:
            raise ValueError(f"Session {session_id} not found")

        session = _sessions[session_id]
        if session["buffer"]:
            residual_audio = np.concatenate(list(session["buffer"]))
            session["buffer"].clear()
        threads = list(session["threads"])

    if residual_audio is not None and len(residual_audio) > 0:
        _transcribe_chunk(session_id, residual_audio)

    for thread in threads:
        thread.join(timeout=10.0)

    with _lock:
        if session_id not in _sessions:
            raise ValueError(f"Session {session_id} not found")
        session = _sessions.pop(session_id)
        full_text = " ".join(
            result.strip() for result in session["results"] if result and result.strip()
        )

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


def get_session_consultation_id(session_id: str) -> int:
    """Get consultation_id for a session."""
    global _sessions
    with _lock:
        if session_id not in _sessions:
            return 0
        return _sessions[session_id]["consultation_id"]
