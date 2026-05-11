"""
Whisper service: standalone FastAPI app that wraps faster-whisper.

Endpoints:
  GET  /health
  POST /transcribe-file    (multipart audio file -> full transcript JSON)
  WS   /ws/transcribe      (binary audio chunks in -> partial/final JSON out)
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from pipeline import StreamingPipeline, transcribe_file_bytes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("whisper-service")

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
WHISPER_PORT = int(os.getenv("WHISPER_PORT", "8001"))

_model = None


def _load_model_sync():
    """Synchronous model load — run inside a thread executor."""
    global _model
    from faster_whisper import WhisperModel
    log.info("Loading faster-whisper model=%s device=%s compute=%s",
             WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE)
    _model = WhisperModel(
        WHISPER_MODEL,
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE_TYPE,
        download_root="/models",
    )
    log.info("Whisper model ready")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load model in a thread so the event loop stays responsive during download.
    # The /health endpoint returns 503 until this completes, which gates the
    # backend healthcheck dependency.
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _load_model_sync)
    yield


app = FastAPI(title="OPD-Vertex Whisper Service", lifespan=lifespan)


@app.get("/health")
async def health():
    if _model is None:
        return JSONResponse(
            status_code=503,
            content={"status": "loading", "model": WHISPER_MODEL},
        )
    return {"status": "ok", "model": WHISPER_MODEL, "device": WHISPER_DEVICE}


@app.post("/transcribe-file")
async def transcribe_file(audio: UploadFile):
    data = await audio.read()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, transcribe_file_bytes, _model, data)
    return result


@app.websocket("/ws/transcribe")
async def ws_transcribe(ws: WebSocket):
    await ws.accept()
    pipeline = StreamingPipeline(_model)
    loop = asyncio.get_event_loop()
    log.info("ws connection opened")
    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if "bytes" in msg and msg["bytes"] is not None:
                # Run synchronous transcription in a thread so the event loop
                # stays free to receive the next audio chunk.
                events = await loop.run_in_executor(None, pipeline.feed, msg["bytes"])
                if events:
                    for event in events:
                        await ws.send_json(event)
                else:
                    # Always ack so the backend doesn't wait 8 s for a response
                    await ws.send_json({"type": "none"})
            elif "text" in msg and msg["text"] is not None:
                if msg["text"] == "FINALIZE":
                    final = await loop.run_in_executor(None, pipeline.finalize)
                    await ws.send_json(final)
                    break
    except WebSocketDisconnect:
        log.info("ws disconnected")
    except Exception as exc:  # noqa: BLE001
        log.exception("ws error")
        await ws.send_json({"type": "error", "message": str(exc)})
    finally:
        log.info("ws connection closed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=WHISPER_PORT)
