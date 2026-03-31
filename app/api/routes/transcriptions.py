"""Transcription API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, HTTPException, Depends
from pydantic import BaseModel

from app.api.deps import (
    get_transcription_service,
    consultation_doc_repository,
    consultation_repository,
)
from app.application.transcriptions.services import TranscriptionApplicationService
from app.domain.clinical_notes.models import ConsultationDocument, TranscriptDocument
from app.domain.consultations.models import ConsultationStatus


class SessionStartRequest(BaseModel):
    consultation_id: int


router = APIRouter(tags=["transcriptions"])


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
    print(f"[WS] WebSocket connected for session {session_id}")

    import asyncio
    from starlette.websockets import WebSocketDisconnect

    try:
        while True:
            try:
                # Wait for audio data with a timeout so we can also check for results
                data = await asyncio.wait_for(websocket.receive_bytes(), timeout=1.0)
                print(f"[WS] Received {len(data)} bytes for session {session_id}")
                chunk_result = service.process_audio_chunk(session_id, data)
                if chunk_result:
                    print(f"[WS] Got chunk result: {chunk_result}")
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
                print(f"[WS] Sending completed result: {result}")
                await websocket.send_json(result)

            # Send current accumulated text
            partial = service.get_partial_transcription(session_id)
            if partial and partial.strip():  # Only send if not empty after stripping
                print(f"[WS] Sending partial: '{partial}'")
                await websocket.send_json({"partial_text": partial})
            elif partial:
                print(f"[WS] Skipping empty partial (before strip): '{partial}'")

    except WebSocketDisconnect:
        print(f"[WS] WebSocket disconnected for session {session_id}")
    except Exception as e:
        print(f"[WS] WebSocket error for session {session_id}: {e}")
        try:
            await websocket.send_json({"error": str(e)})
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


@router.post("/session/{session_id}/complete")
async def complete_transcription(
    session_id: str,
    service: TranscriptionApplicationService = Depends(get_transcription_service),
    doc_repo=Depends(consultation_doc_repository),
    cons_repo=Depends(consultation_repository),
):
    """Complete and finalize transcription session."""
    try:
        print(f"[DEBUG] Saving session {session_id}")
        result = service.complete_transcription(session_id)
        consultation_id = result.consultation_id

        print(
            f"[DEBUG] Save result: consultation_id={consultation_id}, full_text='{result.full_text}'"
        )

        # Save transcription to database
        consultation_doc = doc_repo.get_by_consultation_id(consultation_id)
        if not consultation_doc:
            consultation_doc = ConsultationDocument(
                consultation_id=consultation_id,
                transcript=TranscriptDocument(full_text=result.full_text),
            )
        else:
            consultation_doc.transcript.full_text = result.full_text

        doc_repo.save(consultation_doc)

        # Update consultation status to REVIEW (transcription complete)
        cons_repo.update_status(consultation_id, ConsultationStatus.REVIEW)

        return {
            "consultation_id": consultation_id,
            "full_text": result.full_text,
            "language": result.language,
            "status": "saved",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
