"""Transcription API endpoints — backed by the faster-whisper microservice."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect

from app.api.deps import get_transcription_service
from app.application.transcriptions.services import TranscriptionApplicationService
from app.domain.ai.schemas import FinalTranscript

router = APIRouter(tags=["transcriptions"])
logger = logging.getLogger("opd_vertex.api.transcriptions")

# In-memory stores keyed by session_id.
# _session_chunks: accumulated translated final-chunk events for the results poll.
# _session_transcripts: full FinalTranscript stored after FINALIZE.
_session_chunks: dict[str, list[dict[str, Any]]] = {}
_session_transcripts: dict[str, FinalTranscript] = {}


class SessionStartRequest(BaseModel):
    consultation_id: int


@router.post("/session/start")
async def start_transcription_session(
    request: SessionStartRequest,
    service: TranscriptionApplicationService = Depends(get_transcription_service),
) -> dict:
    """Open a streaming session with the whisper microservice."""
    session_id = await service.start_session(request.consultation_id)
    _session_chunks[session_id] = []
    return {"session_id": session_id, "status": "started"}


@router.get("/session/{session_id}/results")
async def get_session_results(session_id: str) -> dict:
    """Return accumulated transcription chunks for polling after recording stops."""
    chunks = _session_chunks.get(session_id, [])
    transcript = _session_transcripts.get(session_id)
    return {
        "results": chunks,
        "partial_text": "",
        "full_text": transcript.full_text if transcript else "",
        "status": "final" if transcript else "recording",
    }


@router.websocket("/ws/{session_id}")
async def transcription_websocket(
    session_id: str,
    websocket: WebSocket,
    service: TranscriptionApplicationService = Depends(get_transcription_service),
):
    """Proxy audio to the whisper service and stream events back to the client.

    Protocol (matches faster-whisper microservice):
      - Client sends binary frames (raw PCM int16 at 16 kHz)
      - Server forwards events translated to the legacy client format
      - Client sends text "FINALIZE" to end the session
      - Server returns the full annotated FinalTranscript and closes
    """
    await websocket.accept()
    logger.info("Transcription websocket connected session_id=%s", session_id)
    chunk_counter = 0
    try:
        while True:
            msg = await websocket.receive()
            if msg["type"] == "websocket.disconnect":
                break

            if "bytes" in msg and msg["bytes"] is not None:
                async for event in service.push_audio_chunk(session_id, msg["bytes"]):
                    # Accumulate confirmed final segments for the results poll endpoint
                    if event.get("type") == "final":
                        seg = event.get("segment", {})
                        if seg.get("text") and session_id in _session_chunks:
                            _session_chunks[session_id].append({
                                "chunk_id": chunk_counter,
                                "timestamp": round(seg.get("start", 0), 2),
                                "text": seg["text"],
                            })
                            chunk_counter += 1
                    # Forward the raw TC-format event directly to the browser
                    await websocket.send_json(event)

            elif "text" in msg and msg["text"] == "FINALIZE":
                transcript = await service.finalize_session(session_id)
                _session_transcripts[session_id] = transcript
                await websocket.send_json(
                    {"type": "final_full", **transcript.model_dump(mode="json")}
                )
                break

    except WebSocketDisconnect:
        logger.info("Transcription websocket disconnected session_id=%s", session_id)
        transcript = await service.finalize_session(session_id)
        _session_transcripts[session_id] = transcript
    except ValueError as exc:
        logger.warning("Transcription session error: %s", exc)
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    except ConnectionRefusedError:
        logger.warning("Whisper service not reachable for session_id=%s", session_id)
        try:
            await websocket.send_json({"type": "error", "message": "Whisper service is not ready yet — please wait a moment and try again."})
        except Exception:
            pass
    except Exception:
        logger.exception("Transcription websocket error session_id=%s", session_id)
        try:
            await websocket.send_json({"type": "error", "message": "Internal transcription error"})
        except Exception:
            pass


class SaveTranscriptionRequest(BaseModel):
    consultation_id: int
    session_id: str | None = None
    audio_bytes_b64: str | None = None


@router.post("/save-transcription")
async def save_transcription(
    request: SaveTranscriptionRequest,
    service: TranscriptionApplicationService = Depends(get_transcription_service),
) -> dict:
    """Persist the transcription for a consultation to MongoDB."""
    from app.infrastructure.db.mongo.connection import get_database
    from app.application.consultations.services import ConsultationApplicationService

    transcript: FinalTranscript | None = None

    if request.session_id:
        transcript = _session_transcripts.get(request.session_id)
        if transcript is None:
            # Session may still be active — finalize it
            try:
                transcript = await service.finalize_session(request.session_id)
                _session_transcripts[request.session_id] = transcript
            except Exception:
                pass

    if transcript is None and request.audio_bytes_b64:
        import base64
        try:
            audio = base64.b64decode(request.audio_bytes_b64)
            transcript = await service.transcribe_blob(audio)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Audio decode error: {exc}")

    if transcript is None:
        transcript = FinalTranscript(
            full_text="\n".join(
                c["text"] for c in _session_chunks.get(request.session_id or "", [])
                if c.get("text")
            )
        )

    try:
        import asyncio
        from app.api.deps import consultation_doc_repository, get_consultation_app_service
        from app.domain.clinical_notes.models import ConsultationDocument, TranscriptDocument
        from app.domain.consultations.models import ConsultationStatus

        mongo_db = get_database()
        doc_id = await asyncio.to_thread(
            ConsultationApplicationService.persist_transcript,
            mongo_db,
            request.consultation_id,
            transcript,
        )

        # Write / update a ConsultationDocument so the review/generate-report
        # pipeline can find the transcript text via consultation_doc_repository.
        def _upsert_consultation_document():
            repo = consultation_doc_repository()
            existing = repo.get_by_consultation_id(request.consultation_id)
            if existing is not None:
                existing.transcript.full_text = transcript.full_text
                repo.save(existing)
            else:
                repo.save(ConsultationDocument(
                    consultation_id=request.consultation_id,
                    transcript=TranscriptDocument(full_text=transcript.full_text),
                ))

        await asyncio.to_thread(_upsert_consultation_document)

        # Advance consultation status so the overview no longer shows "recording"
        await asyncio.to_thread(
            get_consultation_app_service().update_status,
            request.consultation_id,
            ConsultationStatus.TRANSCRIBING,
        )
        # Clean up in-memory state for this session
        sid = request.session_id
        if sid:
            _session_chunks.pop(sid, None)
            _session_transcripts.pop(sid, None)
        return {"status": "saved", "document_id": doc_id, "full_text": transcript.full_text}
    except Exception as exc:
        logger.exception("Failed to persist transcription for consultation %s", request.consultation_id)
        raise HTTPException(status_code=500, detail=f"Failed to save transcription: {exc}")


class TranscribeBlobRequest(BaseModel):
    consultation_id: int
    audio_bytes_b64: str | None = None


@router.post("/transcribe-blob")
async def transcribe_blob(
    request: TranscribeBlobRequest,
    service: TranscriptionApplicationService = Depends(get_transcription_service),
):
    """One-shot batch transcription for a pre-recorded audio blob (base64-encoded)."""
    import base64
    if not request.audio_bytes_b64:
        raise HTTPException(status_code=400, detail="audio_bytes_b64 is required")
    try:
        audio = base64.b64decode(request.audio_bytes_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 audio data")
    transcript = await service.transcribe_blob(audio)
    return transcript.model_dump(mode="json")
