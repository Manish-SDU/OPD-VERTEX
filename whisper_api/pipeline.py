"""
Streaming pipeline.
"""
from __future__ import annotations

import logging
from typing import Any

import ffmpeg
import numpy as np

log = logging.getLogger("pipeline")


def _decode_to_pcm16k(blob: bytes) -> np.ndarray:
    """WebM/Opus (or anything ffmpeg can read) -> mono float32 16 kHz."""
    if not blob:
        return np.zeros(0, dtype=np.float32)
    try:
        out, _ = (
            ffmpeg.input("pipe:0")
            .output("pipe:1", format="f32le", acodec="pcm_f32le", ac=1, ar=16000, loglevel="error")
            .run(input=blob, capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as exc:
        log.warning("ffmpeg decode failed: %s", exc.stderr.decode("utf-8", "ignore")[:300])
        return np.zeros(0, dtype=np.float32)
    arr = np.frombuffer(out, dtype=np.float32)
    log.info("ffmpeg decoded %d bytes -> %d samples (%.2f s)", len(blob), arr.size, arr.size / 16000)
    return arr


def _seg_to_dict(seg, is_partial: bool) -> dict[str, Any]:
    return {
        "start": float(seg.start),
        "end": float(seg.end),
        "text": seg.text.strip(),
        "avg_logprob": float(seg.avg_logprob) if seg.avg_logprob is not None else None,
        "no_speech_prob": float(seg.no_speech_prob) if seg.no_speech_prob is not None else None,
        "is_partial": is_partial,
    }


# Fast params for live streaming — VAD at 0.3 blocks silence hallucinations without cutting real speech
_STREAMING_KW = dict(
    beam_size=1,
    best_of=1,
    vad_filter=True,
    vad_parameters={"threshold": 0.3, "min_silence_duration_ms": 100},
    condition_on_previous_text=False,
    no_speech_threshold=0.6,
    temperature=0.0,
    language="en",
)

# Accuracy-first params for the final full-buffer pass
_FINAL_KW = dict(
    beam_size=5,
    best_of=5,
    vad_filter=True,
    vad_parameters={"min_silence_duration_ms": 500},
    condition_on_previous_text=False,
    no_speech_threshold=0.6,
    compression_ratio_threshold=2.4,
    temperature=[0.0, 0.2, 0.4],
    language="en",
)


def transcribe_file_bytes(model, blob: bytes) -> dict[str, Any]:
    audio = _decode_to_pcm16k(blob)
    if audio.size == 0:
        return {"segments": [], "full_text": ""}
    segments_iter, info = model.transcribe(audio, **_FINAL_KW)
    segments = [_seg_to_dict(s, is_partial=False) for s in segments_iter]
    return {
        "segments": segments,
        "full_text": " ".join(s["text"] for s in segments).strip(),
        "language": info.language,
        "duration": float(info.duration),
    }


class StreamingPipeline:
    def __init__(self, model):
        self.model = model
        self._raw = bytearray()
        self._emitted_finals: list[dict] = []

    def feed(self, chunk: bytes) -> list[dict[str, Any]]:
        self._raw.extend(chunk)
        log.info("feed: chunk=%d bytes, total_raw=%d bytes", len(chunk), len(self._raw))

        # Must decode the FULL buffer — WebM chunks after the first lack the
        # EBML header and cannot be decoded standalone by ffmpeg.
        audio_full = _decode_to_pcm16k(bytes(self._raw))
        if audio_full.size < 8000:  # need at least 0.5 s before attempting transcription
            log.info("feed: audio too short (%d samples), skipping", audio_full.size)
            return []

        # Transcribe only the last 10 s so latency stays constant.
        _WINDOW = 10 * 16000
        audio = audio_full[-_WINDOW:] if audio_full.size > _WINDOW else audio_full
        log.info("feed: transcribing %d samples (%.2f s)", audio.size, audio.size / 16000)

        try:
            segments_iter, info = self.model.transcribe(audio, **_STREAMING_KW)
            segs = [_seg_to_dict(s, is_partial=True) for s in segments_iter]
            log.info("feed: transcription returned %d segments, lang=%s", len(segs), info.language)
            for s in segs:
                log.info("  seg [%.1f-%.1f] no_speech=%.2f logprob=%.2f text=%r",
                         s["start"], s["end"],
                         s["no_speech_prob"] or 0, s["avg_logprob"] or 0, s["text"])
        except Exception as exc:
            log.exception("feed: transcription error: %s", exc)
            return []

        if not segs:
            log.info("feed: no segments returned")
            return []

        events: list[dict] = []
        for i, seg in enumerate(segs):
            is_last = i == len(segs) - 1
            seg["is_partial"] = is_last
            event_type = "partial" if is_last else "final"
            if event_type == "final":
                key = (round(seg["start"], 2), round(seg["end"], 2))
                already = any(
                    round(e["start"], 2) == key[0] and round(e["end"], 2) == key[1]
                    for e in self._emitted_finals
                )
                if already:
                    continue
                self._emitted_finals.append(seg)
            events.append({"type": event_type, "segment": seg})

        log.info("feed: emitting %d events", len(events))
        return events

    def finalize(self) -> dict[str, Any]:
        """Re-transcribe full buffer with accuracy-first settings."""
        if not self._raw:
            return {"type": "final_full", "segments": [], "full_text": ""}
        payload = transcribe_file_bytes(self.model, bytes(self._raw))
        payload["type"] = "final_full"
        return payload
