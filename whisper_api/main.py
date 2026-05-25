"""Whisper API HTTP Service - runs as a separate container."""

from __future__ import annotations

import os

import ctranslate2
from fastapi import FastAPI, HTTPException, Request

from .models import (
    StartSessionRequest,
    StartSessionResponse,
    TranscriptResult,
    PartialTranscript,
)
from . import service
from .service import (
    init_model,
    start_streaming_session,
    add_audio_chunk,
    finalize_session,
    get_current_text,
    get_session_consultation_id,
)

# Initialize model and store in service module
try:
    device = "cuda" if ctranslate2.get_supported_compute_types("cuda") else "cpu"
except Exception:
    device = "cpu"
model_size = os.environ.get("WHISPER_MODEL_NAME", "large-v3")
service.model = init_model(model_size=model_size, device=device)
print(f"[Whisper] Model initialized model={model_size} device={device}")

app = FastAPI(title="Whisper API", version="1.0.0")


@app.post("/sessions/start", response_model=StartSessionResponse)
async def start_session(request: StartSessionRequest):
    """Start a new transcription session."""
    try:
        session_id = start_streaming_session(
            request.consultation_id,
            request.chunk_duration,
            request.sample_rate,
        )
        return StartSessionResponse(session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sessions/{session_id}/chunk")
async def process_chunk(session_id: str, request: Request):
    """Process audio chunk."""
    try:
        audio_bytes = await request.body()
        result = add_audio_chunk(session_id, audio_bytes)
        if result:
            return result  # Return dict directly, not Pydantic model
        else:
            return {}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"[ERROR] process_chunk failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sessions/{session_id}/complete", response_model=TranscriptResult)
async def complete_session(session_id: str):
    """Complete transcription session."""
    try:
        result = finalize_session(session_id)
        return TranscriptResult(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}/partial", response_model=PartialTranscript)
async def get_partial(session_id: str):
    """Get partial transcription."""
    try:
        text = get_current_text(session_id)
        return PartialTranscript(partial_text=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}/consultation-id")
async def get_consultation_id(session_id: str):
    """Get consultation_id for a session."""
    consultation_id = get_session_consultation_id(session_id)
    return {"consultation_id": consultation_id}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "whisper-api"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
