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
        segments_list = list(segments)
        full_text = " ".join([segment.text for segment in segments_list])

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

                chunk_id = session["chunk_count"]
                session["chunk_count"] += 1
                timestamp = session["timestamp"]
                session["timestamp"] += self.chunk_duration

                thread = threading.Thread(
                    target=self._transcribe_chunk,
                    args=(session_id, chunk_id, audio_chunk, timestamp),
                )
                thread.daemon = True
                thread.start()

                return StreamingTranscriptChunk(
                    chunk_id=chunk_id,
                    text="[processing...]",
                    timestamp=timestamp,
                    is_final=False,
                )

        return None

    def _transcribe_chunk(self, session_id: str, chunk_id: int, audio_chunk: np.ndarray, timestamp: float) -> None:
        """Transcribe audio chunk in background thread."""
        try:
            import tempfile

            import soundfile as sf

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                sf.write(f.name, audio_chunk, self.sample_rate)

                segments, info = self.model.transcribe(f.name, language="en")
                segments_list = list(segments)
                text = " ".join([segment.text for segment in segments_list])

                with self.lock:
                    if session_id in self.sessions:
                        self.sessions[session_id]["results"].append({
                            "chunk_id": chunk_id,
                            "text": text,
                            "timestamp": timestamp,
                            "is_final": True,
                        })

        except Exception as e:
            print(f"[ERROR] Error transcribing chunk: {e}")
            import traceback
            traceback.print_exc()

    def _transcribe_chunk_sync(self, session_id: str, chunk_id: int, audio_chunk: np.ndarray, timestamp: float) -> None:
        """Synchronously transcribe audio chunk (used for final buffer flush)."""
        try:
            import tempfile
            import soundfile as sf

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                sf.write(f.name, audio_chunk, self.sample_rate)

                segments, info = self.model.transcribe(f.name, language="en")
                segments_list = list(segments)
                text = " ".join([segment.text for segment in segments_list])
                
                print(f"[DEBUG] Final chunk {chunk_id}: text='{text}', segments={len(segments_list)}")

                if session_id in self.sessions:
                    self.sessions[session_id]["results"].append({
                        "chunk_id": chunk_id,
                        "text": text,
                        "timestamp": timestamp,
                        "is_final": True,
                    })
                    print(f"[DEBUG] Added final chunk to results")
                else:
                    print(f"[ERROR] Session {session_id} not found when adding final chunk!")

        except Exception as e:
            print(f"[ERROR] Error transcribing final chunk: {e}")
            import traceback
            traceback.print_exc()

    def get_completed_results(self, session_id: str) -> list[dict]:
        """Get completed transcription results without clearing."""
        with self.lock:
            if session_id not in self.sessions:
                return []
            
            session = self.sessions[session_id]
            return session["results"].copy()

    def finalize_session(self, session_id: str) -> TranscriptResult:
        """End streaming and combine all results."""
        with self.lock:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")

            session = self.sessions[session_id]
            
            # Flush any remaining audio in buffer
            if session["buffer"]:
                audio_chunk = np.concatenate(list(session["buffer"]))
                session["buffer"].clear()
                
                chunk_id = session["chunk_count"]
                timestamp = session["timestamp"]
                
                print(f"[DEBUG] Flushing buffer: chunk_id={chunk_id}, audio_samples={len(audio_chunk)}, duration={(len(audio_chunk)/self.sample_rate):.2f}s")
                
                # Transcribe remaining audio synchronously before finalizing
                self._transcribe_chunk_sync(session_id, chunk_id, audio_chunk, timestamp)
            
            session = self.sessions.pop(session_id)
            results = session["results"]
            texts = [r["text"] if isinstance(r, dict) else r for r in results]
            full_text = " ".join(texts)
            
            print(f"[DEBUG] Session finalized: {len(results)} chunks, full_text='{full_text}'")

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
            results = self.sessions[session_id]["results"]
            # Extract text from result dicts
            texts = [r["text"] if isinstance(r, dict) else r for r in results]
            return " ".join(texts)
