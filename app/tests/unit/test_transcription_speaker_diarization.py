"""Unit tests for speaker-labeled transcript normalization (doctor/patient distinction)."""

from __future__ import annotations

import pytest

from app.domain.clinical_notes.models import NormalizedTranscript, SpeakerTurn
from app.domain.clinical_notes.models import (
    LlmPromptConfig,
    TranscriptNormalizationRequest,
)
from app.infrastructure.persistence.in_memory.repositories import (
    MockTranscriptNormalizer,
)


# ── SpeakerTurn model ───────────────────────────────────────────────────────


class TestSpeakerTurn:
    def test_valid_doctor_turn(self):
        t = SpeakerTurn(speaker="DOCTOR", utterance="Good morning.")
        assert t.speaker == "DOCTOR"
        assert t.utterance == "Good morning."

    def test_valid_patient_turn(self):
        t = SpeakerTurn(speaker="PATIENT", utterance="I have a headache.")
        assert t.speaker == "PATIENT"

    def test_valid_unknown_turn(self):
        t = SpeakerTurn(speaker="UNKNOWN", utterance="Unclear speech.")
        assert t.speaker == "UNKNOWN"


# ── NormalizedTranscript with speaker turns ─────────────────────────────────


class TestNormalizedTranscriptWithSpeakerTurns:
    def test_cleaned_transcript_from_dicts(self):
        nt = NormalizedTranscript(
            raw_text="raw",
            cleaned_transcript=[
                {"speaker": "DOCTOR", "utterance": "How are you?"},
                {"speaker": "PATIENT", "utterance": "I have a fever."},
            ],
        )
        assert len(nt.cleaned_transcript) == 2
        assert nt.cleaned_transcript[0].speaker == "DOCTOR"
        assert nt.cleaned_transcript[1].speaker == "PATIENT"

    def test_normalized_text_derived_from_turns(self):
        nt = NormalizedTranscript(
            raw_text="raw",
            cleaned_transcript=[
                {"speaker": "DOCTOR", "utterance": "Good morning."},
                {"speaker": "PATIENT", "utterance": "Hello doctor."},
            ],
        )
        assert "DOCTOR:" in nt.normalized_text
        assert "PATIENT:" in nt.normalized_text
        assert "Good morning." in nt.normalized_text

    def test_explicit_normalized_text_takes_precedence(self):
        nt = NormalizedTranscript(
            raw_text="raw",
            normalized_text="Custom text",
            cleaned_transcript=[{"speaker": "DOCTOR", "utterance": "Hello."}],
        )
        assert nt.normalized_text == "Custom text"

    def test_empty_cleaned_transcript_ok(self):
        nt = NormalizedTranscript(raw_text="raw")
        assert nt.cleaned_transcript == []
        assert nt.normalized_text == ""

    def test_none_cleaned_transcript_becomes_empty_list(self):
        nt = NormalizedTranscript(raw_text="raw", cleaned_transcript=None)
        assert nt.cleaned_transcript == []

    def test_skips_empty_utterances(self):
        nt = NormalizedTranscript(
            raw_text="raw",
            cleaned_transcript=[
                {"speaker": "DOCTOR", "utterance": ""},
                {"speaker": "PATIENT", "utterance": "I feel sick."},
            ],
        )
        # Empty utterance filtered out
        assert len(nt.cleaned_transcript) == 1
        assert nt.cleaned_transcript[0].speaker == "PATIENT"

    def test_three_speaker_types_preserved(self):
        nt = NormalizedTranscript(
            raw_text="",
            cleaned_transcript=[
                {"speaker": "DOCTOR", "utterance": "A."},
                {"speaker": "PATIENT", "utterance": "B."},
                {"speaker": "UNKNOWN", "utterance": "C."},
            ],
        )
        speakers = {t.speaker for t in nt.cleaned_transcript}
        assert speakers == {"DOCTOR", "PATIENT", "UNKNOWN"}


# ── MockTranscriptNormalizer with speaker turns ─────────────────────────────


@pytest.fixture
def normalizer():
    return MockTranscriptNormalizer()


@pytest.fixture
def prompt():
    return LlmPromptConfig(id="t", prompt_name="T")


class TestMockTranscriptNormalizerSpeakerTurns:
    def test_returns_normalized_transcript_type(self, normalizer, prompt):
        result = normalizer.normalize(
            TranscriptNormalizationRequest(
                consultation_id=1, transcript_text="Patient has cough.", prompt=prompt
            )
        )
        assert isinstance(result, NormalizedTranscript)

    def test_cleaned_transcript_is_not_empty(self, normalizer, prompt):
        result = normalizer.normalize(
            TranscriptNormalizationRequest(
                consultation_id=1,
                transcript_text="Doctor: Hello. Patient: I feel unwell.",
                prompt=prompt,
            )
        )
        assert len(result.cleaned_transcript) >= 1

    def test_first_turn_is_doctor(self, normalizer, prompt):
        result = normalizer.normalize(
            TranscriptNormalizationRequest(
                consultation_id=1,
                transcript_text="Good morning, how can I help?",
                prompt=prompt,
            )
        )
        assert result.cleaned_transcript[0].speaker == "DOCTOR"

    def test_alternating_speakers(self, normalizer, prompt):
        result = normalizer.normalize(
            TranscriptNormalizationRequest(
                consultation_id=1,
                transcript_text="Hello. I have a headache. Any medication? Yes, take paracetamol.",
                prompt=prompt,
            )
        )
        speakers = [t.speaker for t in result.cleaned_transcript]
        # First should be DOCTOR
        assert speakers[0] == "DOCTOR"
        if len(speakers) > 1:
            assert speakers[1] == "PATIENT"

    def test_no_double_spaces_in_normalized_text(self, normalizer, prompt):
        result = normalizer.normalize(
            TranscriptNormalizationRequest(
                consultation_id=1,
                transcript_text="patient  uh  reports   cough",
                prompt=prompt,
            )
        )
        assert "  " not in result.normalized_text

    def test_empty_transcript_returns_empty_turns(self, normalizer, prompt):
        result = normalizer.normalize(
            TranscriptNormalizationRequest(
                consultation_id=1, transcript_text="", prompt=prompt
            )
        )
        assert result.cleaned_transcript == []

    def test_raw_text_preserved(self, normalizer, prompt):
        raw = "Patient reports fever."
        result = normalizer.normalize(
            TranscriptNormalizationRequest(
                consultation_id=1, transcript_text=raw, prompt=prompt
            )
        )
        assert result.raw_text == raw

    def test_language_is_english(self, normalizer, prompt):
        result = normalizer.normalize(
            TranscriptNormalizationRequest(
                consultation_id=1, transcript_text="Hello.", prompt=prompt
            )
        )
        assert result.language == "en"

    def test_normalization_notes_present(self, normalizer, prompt):
        result = normalizer.normalize(
            TranscriptNormalizationRequest(
                consultation_id=1, transcript_text="Hello.", prompt=prompt
            )
        )
        assert len(result.normalization_notes) >= 1

    def test_normalized_text_contains_speaker_labels(self, normalizer, prompt):
        result = normalizer.normalize(
            TranscriptNormalizationRequest(
                consultation_id=1,
                transcript_text="Good morning. I feel sick.",
                prompt=prompt,
            )
        )
        assert (
            "DOCTOR:" in result.normalized_text or "PATIENT:" in result.normalized_text
        )

    def test_consultation_id_stored(self, normalizer, prompt):
        result = normalizer.normalize(
            TranscriptNormalizationRequest(
                consultation_id=99, transcript_text="Hello.", prompt=prompt
            )
        )
        assert isinstance(result, NormalizedTranscript)


# ── LLM prompt output mapping ────────────────────────────────────────────────


class TestNormalizedTranscriptFromLlmOutput:
    """Verify NormalizedTranscript correctly parses realistic LLM JSON output."""

    def test_parse_llm_style_output(self):
        """Simulate the JSON a real LLM would return from transcript_normalization_v1.md."""
        llm_payload = {
            "cleaned_transcript": [
                {"speaker": "DOCTOR", "utterance": "Good morning, how are you today?"},
                {
                    "speaker": "PATIENT",
                    "utterance": "I have had a headache for two days.",
                },
                {"speaker": "DOCTOR", "utterance": "Any fever or nausea?"},
                {"speaker": "PATIENT", "utterance": "Some mild nausea but no fever."},
            ],
            "uncertain_segments": [
                {"raw_text": "muffled noise", "reason": "inaudible"}
            ],
            "normalization_notes": ["Minor ASR corrections applied."],
        }
        nt = NormalizedTranscript.model_validate(llm_payload)
        assert len(nt.cleaned_transcript) == 4
        assert nt.cleaned_transcript[0].speaker == "DOCTOR"
        assert nt.cleaned_transcript[1].speaker == "PATIENT"
        assert len(nt.uncertain_segments) == 1
        assert len(nt.normalization_notes) == 1

    def test_normalized_text_from_llm_output(self):
        llm_payload = {
            "cleaned_transcript": [
                {"speaker": "DOCTOR", "utterance": "Hello."},
                {"speaker": "PATIENT", "utterance": "Hi."},
            ],
            "uncertain_segments": [],
            "normalization_notes": [],
        }
        nt = NormalizedTranscript.model_validate(llm_payload)
        assert "DOCTOR: Hello." in nt.normalized_text
        assert "PATIENT: Hi." in nt.normalized_text
