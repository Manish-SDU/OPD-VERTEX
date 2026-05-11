"""Unit tests for transcript quality / hallucination flagging."""

from __future__ import annotations

from app.application.transcriptions.quality import QualityConfig, annotate, flag_segment
from app.domain.ai.schemas import FinalTranscript, TranscriptSegment


def _seg(text: str, lp: float = -0.3, ns: float = 0.05) -> TranscriptSegment:
    return TranscriptSegment(start=0, end=1, text=text, avg_logprob=lp, no_speech_prob=ns)


def test_artifact_phrase_flagged():
    flags = flag_segment(_seg("Thanks for watching"), QualityConfig())
    assert "artifact_phrase" in flags


def test_low_logprob_flagged():
    flags = flag_segment(_seg("the patient", lp=-1.9), QualityConfig())
    assert "very_low_logprob" in flags


def test_text_in_silence_flagged():
    flags = flag_segment(_seg("uhh", ns=0.95), QualityConfig())
    assert "text_in_silence" in flags


def test_repeated_ngram_flagged():
    text = "and the cough was and the cough was and the cough was and the cough was"
    flags = flag_segment(
        _seg(text), QualityConfig(repeated_ngram_n=4, repeated_ngram_threshold=3)
    )
    assert "repeated_ngram" in flags


def test_clean_segment_no_flags():
    flags = flag_segment(_seg("Patient reports mild headache for two days."), QualityConfig())
    assert flags == []


def test_annotate_aggregates_rate():
    t = FinalTranscript(
        segments=[
            _seg("Patient is well."),
            _seg("Thanks for watching"),  # artifact
            _seg("Mild fever."),
        ]
    )
    annotate(t)
    assert 0.3 < t.hallucination_rate < 0.4  # 1 of 3
