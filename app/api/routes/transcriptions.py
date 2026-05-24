"""Transcription API endpoints."""

from __future__ import annotations

from logging import getLogger

from fastapi import APIRouter, WebSocket, HTTPException, Depends
from pydantic import BaseModel

from app.api.deps import get_transcription_service
from app.application.transcriptions.services import TranscriptionApplicationService


class SessionStartRequest(BaseModel):
    consultation_id: int


router = APIRouter(tags=["transcriptions"])
logger = getLogger("opd_vertex.api.transcriptions")


@router.post("/session/start")
async def start_transcription_session(
    request: SessionStartRequest,
    service: TranscriptionApplicationService = Depends(get_transcription_service),
) -> dict:
    """Start a new transcription session."""
    session_id = service.start_transcription_session(request.consultation_id)
    return {"session_id": session_id, "status": "started"}


@router.websocket("/ws/{session_id}")
async def transcription_websocket(
    session_id: str,
    websocket: WebSocket,
    service: TranscriptionApplicationService = Depends(get_transcription_service),
):
    """WebSocket endpoint for streaming transcription."""
    await websocket.accept()
    logger.info("Transcription websocket connected session_id=%s", session_id)

    import asyncio
    from starlette.websockets import WebSocketDisconnect

    try:
        while True:
            try:
                # Wait for any message (bytes or text) with a timeout
                message = await asyncio.wait_for(websocket.receive(), timeout=1.0)

                # Handle text control messages (e.g. FINALIZE)
                if message.get("text") is not None:
                    text_msg = message["text"]
                    logger.info(
                        "Received text control message session_id=%s msg=%s",
                        session_id,
                        text_msg,
                    )
                    if text_msg.strip().upper() == "FINALIZE":
                        break
                    continue

                data = message.get("bytes")
                if not data:
                    continue

                logger.debug(
                    "Received transcription audio chunk session_id=%s bytes=%s",
                    session_id,
                    len(data),
                )
                chunk_result = service.process_audio_chunk(session_id, data)
                if chunk_result:
                    logger.debug(
                        "Streaming chunk result ready session_id=%s chunk_id=%s is_final=%s",
                        session_id,
                        chunk_result.chunk_id,
                        chunk_result.is_final,
                    )
                    await websocket.send_json(
                        {
                            "chunk_id": chunk_result.chunk_id,
                            "text": chunk_result.text,
                            "timestamp": chunk_result.timestamp,
                            "is_final": chunk_result.is_final,
                        }
                    )
            except asyncio.TimeoutError:
                # Timeout is normal - just continue to check for results
                pass

            # Check for completed results from background threads
            completed = service.get_completed_results(session_id)
            for result in completed:
                logger.debug(
                    "Sending completed transcription result session_id=%s keys=%s",
                    session_id,
                    sorted(result.keys()),
                )
                await websocket.send_json(result)

            # Send current accumulated text
            partial = service.get_partial_transcription(session_id)
            if partial and partial.strip():  # Only send if not empty after stripping
                logger.debug(
                    "Sending partial transcription session_id=%s characters=%s",
                    session_id,
                    len(partial),
                )
                await websocket.send_json({"partial_text": partial})

    except WebSocketDisconnect:
        logger.info("Transcription websocket disconnected session_id=%s", session_id)
    except Exception as exc:
        logger.exception(
            "Transcription websocket error session_id=%s error=%s",
            session_id,
            exc,
        )
        try:
            await websocket.send_json({"error": str(exc)})
        except Exception:
            pass


@router.get("/session/{session_id}/results")
async def get_session_results(
    session_id: str,
    service: TranscriptionApplicationService = Depends(get_transcription_service),
) -> dict:
    """Get accumulated results for a session."""
    results = service.get_completed_results(session_id)
    partial = service.get_partial_transcription(session_id)
    return {
        "results": results,
        "partial_text": partial,
    }


class InjectDemoRequest(BaseModel):
    text: str


@router.post("/session/{session_id}/inject-demo")
async def inject_demo_text(
    session_id: str,
    request: InjectDemoRequest,
    service: TranscriptionApplicationService = Depends(get_transcription_service),
) -> dict:
    """Inject text directly into a session (demo / no-mic mode)."""
    service.inject_demo_text(session_id, request.text)
    return {"status": "injected", "characters": len(request.text)}


@router.post("/session/{session_id}/complete")
async def complete_transcription(
    session_id: str,
    service: TranscriptionApplicationService = Depends(get_transcription_service),
):
    """Complete and finalize transcription session."""
    try:
        result = service.finalize_and_persist_transcription(session_id)

        return {
            "consultation_id": result.consultation_id,
            "full_text": result.full_text,
            "language": result.language,
            "status": "saved",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SaveTranscriptionRequest(BaseModel):
    consultation_id: int
    session_id: str


@router.post("/save-transcription")
async def save_transcription(
    request: SaveTranscriptionRequest,
    service: TranscriptionApplicationService = Depends(get_transcription_service),
):
    """Save partial chunks from temp storage to main database."""
    try:
        result = service.persist_saved_transcription(
            request.consultation_id, request.session_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "saved",
        "consultation_id": request.consultation_id,
        "full_text": result.full_text,
    }
