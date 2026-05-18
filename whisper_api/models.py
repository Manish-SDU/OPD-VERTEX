"""Pydantic models for Whisper API requests and responses."""

from pydantic import BaseModel


class StartSessionRequest(BaseModel):
    """Request to start a new transcription session."""

    consultation_id: int
    chunk_duration: float = 2.0
    sample_rate: int = 16000


class StartSessionResponse(BaseModel):
    """Response when session starts."""

    session_id: str
    status: str = "started"


class TranscriptChunk(BaseModel):
    """A chunk of transcribed audio."""

    chunk_id: int
    text: str
    timestamp: float
    is_final: bool = False


class TranscriptResult(BaseModel):
    """Final transcription result."""

    consultation_id: int
    full_text: str
    language: str = "en"


class PartialTranscript(BaseModel):
    """Partial transcription result."""

    partial_text: str
