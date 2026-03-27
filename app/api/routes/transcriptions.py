"""Transcription API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, HTTPException, Depends

from app.api.deps import get_transcription_service
from app.application.transcriptions.services import TranscriptionApplicationService

router = APIRouter(prefix="/transcriptions", tags=["transcriptions"])


@router.post("/session/start")
async def start_transcription_session(
    consultation_id: int,
    service: TranscriptionApplicationService = Depends(get_transcription_service),
) -> dict:
    """Start a new transcription session."""
    session_id = service.start_transcription_session(consultation_id)
    return {"session_id": session_id, "status": "started"}


@router.websocket("/ws/{session_id}")
async def transcription_websocket(
    session_id: str,
    websocket: WebSocket,
    service: TranscriptionApplicationService = Depends(get_transcription_service),
):
    """WebSocket endpoint for streaming transcription."""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_bytes()

            result = service.process_audio_chunk(session_id, data)

            if result:
                await websocket.send_json(
                    {
                        "chunk_id": result.chunk_id,
                        "text": result.text,
                        "timestamp": result.timestamp,
                    }
                )

            partial = service.get_partial_transcription(session_id)
            await websocket.send_json({"partial_text": partial})

    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close(code=1000)


@router.post("/session/{session_id}/complete")
async def complete_transcription(
    session_id: str,
    service: TranscriptionApplicationService = Depends(get_transcription_service),
):
    """Complete and finalize transcription session."""
    try:
        result = service.complete_transcription(session_id)
        return {
            "consultation_id": result.consultation_id,
            "full_text": result.full_text,
            "language": result.language,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))