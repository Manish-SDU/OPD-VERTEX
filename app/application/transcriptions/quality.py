"""
Transcript quality heuristics — confidence + hallucination flagging.

Whisper is prone to inventing text from silence ("Thanks for watching"),
repeating phrases when the audio is unclear, and producing low-confidence
runs. We flag these without altering the underlying transcript so the
doctor can decide.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from app.domain.ai.schemas import FinalTranscript, TranscriptSegment

DEFAULT_ARTIFACTS = (
    "thanks for watching",
    "thank you for watching",
    "subscribe to my channel",
    "like and subscribe",
    "[music]",
    "[applause]",
    "♪",
)


@dataclass
class QualityConfig:
    low_confidence_logprob: float = -1.0
    halluc_logprob: float = -1.5
    halluc_no_speech_prob: float = 0.7
    repeated_ngram_n: int = 4
    repeated_ngram_threshold: int = 3
    artifact_phrases: tuple[str, ...] = DEFAULT_ARTIFACTS


def _ngrams(words: list[str], n: int) -> list[tuple[str, ...]]:
    if len(words) < n:
        return []
    return [tuple(words[i:i + n]) for i in range(len(words) - n + 1)]


def _detect_repeated_ngram(text: str, n: int, threshold: int) -> bool:
    words = re.findall(r"\w+", text.lower())
    grams = _ngrams(words, n)
    if not grams:
        return False
    counts: dict[tuple[str, ...], int] = {}
    for g in grams:
        counts[g] = counts.get(g, 0) + 1
        if counts[g] >= threshold:
            return True
    return False


def flag_segment(seg: TranscriptSegment, cfg: QualityConfig) -> list[str]:
    flags: list[str] = []
    text_l = seg.text.strip().lower()
    if not text_l:
        return flags
    if any(a in text_l for a in cfg.artifact_phrases):
        flags.append("artifact_phrase")
    if seg.avg_logprob is not None and seg.avg_logprob < cfg.halluc_logprob:
        flags.append("very_low_logprob")
    if (
        seg.no_speech_prob is not None
        and seg.no_speech_prob > cfg.halluc_no_speech_prob
        and len(text_l) > 0
    ):
        flags.append("text_in_silence")
    if _detect_repeated_ngram(seg.text, cfg.repeated_ngram_n, cfg.repeated_ngram_threshold):
        flags.append("repeated_ngram")
    return flags


def annotate(transcript: FinalTranscript, cfg: QualityConfig | None = None) -> FinalTranscript:
    cfg = cfg or QualityConfig()
    flagged = 0
    confs: list[float] = []
    for seg in transcript.segments:
        seg.hallucination_flags = flag_segment(seg, cfg)
        if seg.hallucination_flags:
            flagged += 1
        if seg.avg_logprob is not None:
            confs.append(seg.avg_logprob)
    n = len(transcript.segments)
    transcript.hallucination_rate = (flagged / n) if n else 0.0
    transcript.confidence_avg = (sum(confs) / len(confs)) if confs else None
    return transcript


def make_config_from_yaml(d: dict) -> QualityConfig:
    return QualityConfig(
        low_confidence_logprob=d.get("low_confidence_logprob", -1.0),
        halluc_logprob=d.get("halluc_logprob", -1.5),
        halluc_no_speech_prob=d.get("halluc_no_speech_prob", 0.7),
        repeated_ngram_n=d.get("repeated_ngram_n", 4),
        repeated_ngram_threshold=d.get("repeated_ngram_threshold", 3),
        artifact_phrases=tuple(s.lower() for s in d.get("artifact_phrases", DEFAULT_ARTIFACTS)),
    )
