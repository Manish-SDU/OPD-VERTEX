"""Transcription application service — async, backed by the whisper microservice."""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from app.application.transcriptions.quality import QualityConfig, annotate
from app.domain.ai.schemas import FinalTranscript
from app.infrastructure.ai.transcription.whisper_client import (
    FasterWhisperRemoteSTT,
    _RemoteStream,
)

log = logging.getLogger(__name__)

_sessions: dict[str, _RemoteStream] = {}


class TranscriptionApplicationService:
    """Orchestrate audio transcription via the faster-whisper microservice."""

    def __init__(self, stt: FasterWhisperRemoteSTT, quality_cfg: QualityConfig | None = None):
        self.stt = stt
        self.quality_cfg = quality_cfg or QualityConfig()

    async def start_session(self, consultation_id: int) -> str:
        """Open a WebSocket stream to the whisper service and return a session id."""
        session_id = f"c{consultation_id}-{id(object())}"
        stream = await self.stt.open_stream(session_id)
        _sessions[session_id] = stream
        log.info("Transcription session started: %s", session_id)
        return session_id

    async def push_audio_chunk(
        self, session_id: str, blob: bytes
    ) -> AsyncIterator[dict[str, Any]]:
        """Forward audio bytes to the whisper service, yield partial/final events."""
        stream = _sessions.get(session_id)
        if stream is None:
            raise ValueError(f"Unknown transcription session: {session_id}")
        async for event in stream.push_audio(blob):
            yield event

    async def finalize_session(self, session_id: str) -> FinalTranscript:
        """Send FINALIZE, receive the accuracy-first transcript, annotate quality."""
        stream = _sessions.pop(session_id, None)
        if stream is None:
            log.warning("finalize_session: unknown session %s", session_id)
            return FinalTranscript()
        transcript = await stream.finalize()
        return annotate(transcript, self.quality_cfg)

    async def transcribe_blob(self, audio: bytes) -> FinalTranscript:
        """One-shot batch transcription (for uploaded audio files)."""
        transcript = await self.stt.transcribe_blob(audio)
        return annotate(transcript, self.quality_cfg)
