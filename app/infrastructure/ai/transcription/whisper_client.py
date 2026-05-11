"""HTTP + WebSocket client for the faster-whisper microservice."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

import httpx
import websockets

from app.domain.ai.schemas import FinalTranscript, TranscriptSegment

log = logging.getLogger(__name__)


class _RemoteStream:
    """WebSocket session to the whisper /ws/transcribe endpoint."""

    def __init__(self, ws_url: str):
        self._ws_url = ws_url
        self._ws: websockets.WebSocketClientProtocol | None = None

    async def _connect(self):
        if self._ws is None:
            self._ws = await websockets.connect(self._ws_url, max_size=8 * 1024 * 1024)

    async def push_audio(self, blob: bytes) -> AsyncIterator[dict[str, Any]]:
        """Send a binary audio chunk and yield transcription events.

        TC pipeline emits 0-N final events then exactly 1 partial (or 1 none).
        We read until we see 'partial' or 'none' so all events are forwarded.
        """
        await self._connect()
        await self._ws.send(blob)
        try:
            while True:
                msg = await asyncio.wait_for(self._ws.recv(), timeout=8.0)
                ev = json.loads(msg)
                t = ev.get("type")
                if t == "none":
                    break
                yield ev
                if t == "partial":
                    break  # partial is always last in the batch
        except asyncio.TimeoutError:
            log.warning("whisper did not respond within 8 s for this chunk")
        except Exception:  # noqa: BLE001
            return

    async def finalize(self) -> FinalTranscript:
        """Send FINALIZE and await the accuracy-first full transcript."""
        if self._ws is None:
            return FinalTranscript()
        await self._ws.send("FINALIZE")
        payload: dict = {}
        try:
            while True:
                msg = await asyncio.wait_for(self._ws.recv(), timeout=300.0)
                ev = json.loads(msg)
                if ev.get("type") == "final_full":
                    payload = ev
                    break
                if ev.get("type") == "error":
                    log.warning("whisper finalize error: %s", ev.get("message"))
                    break
                log.debug("finalize: discarding stale message type=%s", ev.get("type"))
        except Exception:
            log.exception("finalize: error waiting for final_full")
        finally:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        segs = [
            TranscriptSegment(**{k: v for k, v in s.items() if k in TranscriptSegment.model_fields})
            for s in payload.get("segments", [])
        ]
        confs = [s.avg_logprob for s in segs if s.avg_logprob is not None]
        return FinalTranscript(
            segments=segs,
            full_text=payload.get("full_text", ""),
            confidence_avg=(sum(confs) / len(confs)) if confs else None,
            language=payload.get("language"),
            duration_s=payload.get("duration"),
        )


class FasterWhisperRemoteSTT:
    """Client for the faster-whisper microservice."""

    def __init__(
        self,
        url: str,
        ws_path: str = "/ws/transcribe",
        file_path: str = "/transcribe-file",
    ):
        self.url = url.rstrip("/")
        self.ws_path = ws_path
        self.file_path = file_path

    def _ws_url(self) -> str:
        return (
            self.url.replace("http://", "ws://").replace("https://", "wss://")
            + self.ws_path
        )

    async def open_stream(self, session_id: str) -> _RemoteStream:
        return _RemoteStream(self._ws_url())

    async def transcribe_blob(self, audio: bytes) -> FinalTranscript:
        """One-shot batch transcription via HTTP POST."""
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(
                self.url + self.file_path,
                files={"audio": ("audio.bin", audio)},
            )
            r.raise_for_status()
            payload = r.json()
        segs = [
            TranscriptSegment(**{k: v for k, v in s.items() if k in TranscriptSegment.model_fields})
            for s in payload.get("segments", [])
        ]
        confs = [s.avg_logprob for s in segs if s.avg_logprob is not None]
        return FinalTranscript(
            segments=segs,
            full_text=payload.get("full_text", ""),
            confidence_avg=(sum(confs) / len(confs)) if confs else None,
            language=payload.get("language"),
            duration_s=payload.get("duration"),
        )
