"""Faster-Whisper streaming transcription adapter with pre-downloaded models."""

from __future__ import annotations

import os
import threading
import uuid
from collections import deque
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

from app.domain.transcriptions.models import (
    StreamingTranscriptChunk,
    StreamingTranscriptionService,
    TranscriptResult,
    TranscriptionService,
)


class FasterWhisperTranscriptionService(TranscriptionService):
    """Batch transcription service for complete audio files."""

    def __init__(self, model_size: str = "base", device: str = "cuda"):
        # Set HuggingFace cache to models directory
        models_dir = Path(__file__).parent.parent.parent / "models"
        os.environ['HF_HOME'] = str(models_dir)
        
        self.model = WhisperModel(
            model_size,
            device=device,
        )

    def transcribe(self, audio_path: str) -> TranscriptResult:
        """Transcribe complete audio file."""
        segments, info = self.model.transcribe(audio_path, language="en")
        full_text = " ".join([segment.text for segment in segments])

        return TranscriptResult(
            consultation_id=0,
            file_path=audio_path,
            full_text=full_text,
            language=info.language,
        )


class StreamingFasterWhisperService(StreamingTranscriptionService):
    """Streaming transcription service that processes audio in chunks."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cuda",
        chunk_duration: float = 2.0,
        sample_rate: int = 16000,
    ):
        # Set HuggingFace cache to models directory
        models_dir = Path(__file__).parent.parent.parent / "models"
        os.environ['HF_HOME'] = str(models_dir)
        
        self.model = WhisperModel(
            model_size,
            device=device,
        )
        self.chunk_duration = chunk_duration
        self.sample_rate = sample_rate
        self.chunk_size = int(chunk_duration * sample_rate)

        self.sessions: dict[str, dict] = {}
        self.lock = threading.Lock()

    def start_streaming(self, consultation_id: int) -> str:
        """Initialize a streaming session."""
        session_id = str(uuid.uuid4())
        with self.lock:
            self.sessions[session_id] = {
                "consultation_id": consultation_id,
                "buffer": deque(),
                "results": [],
                "chunk_count": 0,
                "timestamp": 0.0,
            }
        return session_id

    def add_audio_chunk(
        self, session_id: str, audio_bytes: bytes
    ) -> StreamingTranscriptChunk | None:
        """Add audio chunk and optionally return transcription."""
        with self.lock:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")

            session = self.sessions[session_id]

            audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(
                np.float32
            ) / 32768.0
            session["buffer"].append(audio_data)

            total_samples = sum(len(chunk) for chunk in session["buffer"])

            if total_samples >= self.chunk_size:
                audio_chunk = np.concatenate(list(session["buffer"]))
                session["buffer"].clear()

                thread = threading.Thread(
                    target=self._transcribe_chunk,
                    args=(session_id, audio_chunk),
                )
                thread.daemon = True
                thread.start()

                chunk_id = session["chunk_count"]
                session["chunk_count"] += 1

                return StreamingTranscriptChunk(
                    chunk_id=chunk_id,
                    text="[processing...]",
                    timestamp=session["timestamp"],
                    is_final=False,
                )

        return None

    def _transcribe_chunk(self, session_id: str, audio_chunk: np.ndarray) -> None:
        """Transcribe audio chunk in background thread."""
        try:
            import tempfile

            import soundfile as sf

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                sf.write(f.name, audio_chunk, self.sample_rate)

                segments, info = self.model.transcribe(f.name, language="en")
                text = " ".join([segment.text for segment in segments])

                with self.lock:
                    if session_id in self.sessions:
                        self.sessions[session_id]["results"].append(text)

        except Exception as e:
            print(f"Error transcribing chunk: {e}")

    def finalize_session(self, session_id: str) -> TranscriptResult:
        """End streaming and combine all results."""
        with self.lock:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")

            session = self.sessions.pop(session_id)
            full_text = " ".join(session["results"])

        return TranscriptResult(
            consultation_id=session["consultation_id"],
            file_path="",
            full_text=full_text,
        )

    def get_current_text(self, session_id: str) -> str:
        """Get transcription accumulated so far."""
        with self.lock:
            if session_id not in self.sessions:
                return ""
            return " ".join(self.sessions[session_id]["results"])
