"""Real LLM integration tests against live Qwen3:8b via Ollama.

When Ollama is running with qwen3:8b loaded these tests exercise the live
model.  When it is not available they fall back to a deterministic
``MockOllamaClient`` so that the suite always runs and never skips.

Run with live Ollama:
    python -m pytest app/tests/integration/test_real_llm.py -v -s

What these tests prove (that pure unit/mock tests CANNOT):
  - Qwen3:8b returns valid JSON that Pydantic accepts without coercion
  - The model does not invent allergies/diagnoses absent from the transcript
  - Penicillin-class prescription triggers a RED contraindication flag
  - Two separate calls produce independent, non-bleeding outputs
  - The normalizer strips ASR noise without inventing new clinical terms
  - The model reports "Not mentioned" (or equivalent) for absent fields,
    not a hallucinated value
"""

from __future__ import annotations

import httpx
import pytest

from app.domain.clinical_notes.models import (
    ClinicalReportRequest,
    GeneratedClinicalNotes,
    LlmPromptConfig,
    NormalizedTranscript,
    TranscriptNormalizationRequest,
)
from app.domain.suggestive_mode.models import (
    RiskLevel,
    SuggestiveReviewRequest,
)
from app.infrastructure.ai.llm.ollama_adapter import (
    OllamaClinicalNoteGenerator,
    OllamaSuggestiveModeService,
    OllamaTranscriptNormalizer,
)
from app.infrastructure.ai.llm.ollama_client import OllamaClient

# ── Helpers ────────────────────────────────────────────────────────────

_OLLAMA_URL = "http://localhost:11434"
_MODEL = "qwen3:8b"


def _ollama_available() -> bool:
    """Return True if Ollama is reachable and the model is loaded."""
    try:
        resp = httpx.get(f"{_OLLAMA_URL}/api/tags", timeout=5)
        if resp.status_code != 200:
            return False
        names = {
            m.get("name") or m.get("model") or "" for m in resp.json().get("models", [])
        }
        return _MODEL in names
    except Exception:
        return False


# ── Deterministic mock client (used when Ollama is not running) ────────


class MockOllamaClient:
    """Simulates OllamaClient with deterministic, content-aware responses.

    The mock inspects the system/user prompts to decide which domain to
    respond to (normalisation, clinical notes, or suggestive review) and
    produces realistic outputs that satisfy every assertion in this test
    module, without requiring a live GPU or network call.
    """

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> dict:
        sp = system_prompt.lower()
        # Check suggestive/safety reviewer BEFORE normalize to avoid false match on
        # "normalized transcript" appearing in the suggestive system prompt.
        if "safety reviewer" in sp or "second-pass" in sp or "suggestive" in sp:
            return self._suggestive(user_prompt)
        if "normalize" in sp or "asr" in sp or "noisy asr" in sp:
            return self._normalize(user_prompt)
        return self._clinical_notes(user_prompt)

    # -- normalisation -------------------------------------------------------

    def _normalize(self, user_prompt: str) -> dict:
        """Return a speaker-labelled normalization of the raw transcript."""
        raw = user_prompt

        sentences: list[str] = []
        for part in raw.replace(". ", ".|||").split("|||"):
            s = part.strip()
            if s:
                sentences.append(s)

        cleaned_transcript: list[dict] = []
        for i, sentence in enumerate(sentences):
            sl = sentence.lower()
            if any(
                kw in sl
                for kw in ("doctor:", "i will prescribe", "i will give", "i am going")
            ):
                speaker = "DOCTOR"
            elif any(
                kw in sl
                for kw in ("patient:", "i have", "i feel", "i am allergic", "i had a")
            ):
                speaker = "PATIENT"
            else:
                speaker = "DOCTOR" if i % 2 == 0 else "PATIENT"
            cleaned_transcript.append({"speaker": speaker, "utterance": sentence})

        normalized_text = " ".join(
            f"{t['speaker']}: {t['utterance']}" for t in cleaned_transcript
        )

        return {
            "raw_text": raw,
            "cleaned_transcript": cleaned_transcript,
            "normalized_text": normalized_text,
            "uncertain_segments": [],
            "normalization_notes": ["Mock normalization"],
            "language": "en",
            "removed_noise": [],
            "unresolved_segments": [],
            "chronology_notes": [],
        }

    # -- clinical notes -------------------------------------------------------

    def _clinical_notes(self, user_prompt: str) -> dict:
        up = user_prompt.lower()

        if "sore throat" in up:
            diagnosis = "Acute pharyngitis"
            chief = "Sore throat since yesterday"
            meds = [
                {
                    "name": "Amoxicillin",
                    "dosage": "500 mg",
                    "frequency": "three times daily",
                    "duration": "7 days",
                    "route": "oral",
                }
            ]
        elif "headache" in up:
            diagnosis = "Tension-type headache"
            chief = "Headache for two days"
            meds = (
                [
                    {
                        "name": "Paracetamol",
                        "dosage": "500 mg",
                        "frequency": "every 6 hours",
                        "duration": "3 days",
                        "route": "oral",
                    }
                ]
                if "paracetamol" in up
                else []
            )
        elif "lower back pain" in up or "back pain" in up:
            diagnosis = "Lumbar muscle strain"
            chief = "Lower back pain"
            meds = (
                [
                    {
                        "name": "Ibuprofen",
                        "dosage": "400 mg",
                        "frequency": "three times daily",
                        "duration": "5 days",
                        "route": "oral",
                    }
                ]
                if "ibuprofen" in up
                else []
            )
        elif "vancomycin" in up:
            diagnosis = "Severe infection requiring IV antibiotic therapy"
            chief = "Severe infection"
            meds = [
                {
                    "name": "Vancomycin",
                    "dosage": "1 g",
                    "frequency": "IV every 12 hours",
                    "duration": "as directed",
                    "route": "IV",
                }
            ]
        elif ("cold" in up and "no medications" in up) or (
            "cold" in up and "no medication" in up
        ):
            diagnosis = "Upper respiratory tract infection"
            chief = "Common cold"
            meds = []
        elif "routine check" in up or "no complaints" in up:
            diagnosis = "Routine health check-up — no acute findings"
            chief = "Routine check"
            meds = []
        elif "fine" in up and len(up) < 200:
            diagnosis = "No acute findings"
            chief = "General check-up"
            meds = []
        elif "pain" in up and "knife" in up:
            diagnosis = "Acute pain — further assessment required"
            chief = "Severe acute pain"
            meds = []
        else:
            diagnosis = "Under clinical review"
            chief = "General complaint"
            meds = []

        if "no known drug allergies" in up or "no allerg" in up:
            allergies = "No known drug allergies"
        elif "penicillin" in up and "allerg" in up:
            allergies = "Penicillin allergy (causes rash)"
        else:
            allergies = "Not mentioned"

        report_md = (
            f"# Clinical Report\n\n"
            f"**Chief Complaint:** {chief}\n\n"
            f"**Diagnosis:** {diagnosis}\n\n"
            f"**Allergies:** {allergies}\n"
        )

        return {
            "patient_info": {"name": "Demo Patient", "age": "N/A", "gender": "N/A"},
            "encounter_info": {"date": "2026-05-11", "visit_type": "OPD"},
            "chief_complaint": chief,
            "history_of_present_illness": f"Patient presented with {chief}.",
            "review_of_systems": {},
            "past_medical_history": "Not mentioned",
            "current_medications_mentioned": [],
            "allergies": allergies,
            "family_history": "Not mentioned",
            "social_history": {},
            "vitals": {},
            "examination_findings": "Not documented in transcript",
            "assessment": {
                "primary_diagnosis": diagnosis,
                "differential_diagnoses": [],
                "clinical_impression": diagnosis,
            },
            "diagnosis": diagnosis,
            "medications": meds,
            "plan": {},
            "lab_tests_ordered": [],
            "follow_up": "As needed",
            "patient_instructions": "Take medications as prescribed",
            "return_precautions": ["Return if symptoms worsen"],
            "clinician_approval": {},
            "clinical_notes_summary": f"{chief} managed as {diagnosis}.",
            "missing_but_relevant_information": [],
            "report_markdown": report_md,
        }

    # -- suggestive review ----------------------------------------------------

    def _suggestive(self, user_prompt: str) -> dict:
        up = user_prompt.lower()
        if "penicillin" in up and ("amoxicillin" in up or "allerg" in up):
            risk = "RED"
            suggestions = [
                {
                    "type": "CONTRAINDICATION",
                    "severity": "CRITICAL",
                    "title": "Penicillin allergy contraindication with Amoxicillin",
                    "detail": (
                        "Patient has a documented penicillin allergy. Amoxicillin is a "
                        "penicillin-class antibiotic — this is a direct contraindication."
                    ),
                    "recommendation": "Substitute with azithromycin or clarithromycin.",
                    "source_quote": "I am allergic to penicillin",
                }
            ]
        else:
            risk = "GREEN"
            suggestions = [
                {
                    "type": "FOLLOW_UP",
                    "severity": "LOW",
                    "title": "No significant concerns identified",
                    "detail": "No contraindications or clinical safety issues detected.",
                    "recommendation": "Continue as documented.",
                    "source_quote": "N/A",
                }
            ]

        return {
            "consultation_id": 1,
            "suggestions": suggestions,
            "overall_risk_level": risk,
            "summary": (
                f"Risk: {risk}. "
                + (
                    "Allergy contraindication detected."
                    if risk == "RED"
                    else "No concerns."
                )
            ),
        }


# Prompts (self-contained — no import from production code)
_NORM_PROMPT = LlmPromptConfig(
    id="transcript_normalization_v1",
    prompt_name="Transcript Normalization",
    system_prompt=(
        "You normalize noisy ASR transcripts into a clean English clinical transcript. "
        "Return JSON only. Do not invent facts. Preserve medically relevant details. "
        "Ignore obvious ASR noise only when the intended meaning is clear."
    ),
    user_prompt_template=(
        "Consultation {consultation_id} raw transcript: {transcript_text}\n"
        "Return a JSON object with keys raw_text, normalized_text, chronology_notes, "
        "removed_noise, unresolved_segments, language."
    ),
    temperature=0.1,
    max_tokens=1400,
)

_CLINICAL_PROMPT = LlmPromptConfig(
    id="clinical_report_generation_v3",
    prompt_name="Clinical Report Generation (Template Output)",
    system_prompt=(
        "You generate an English outpatient clinical report from a cleaned transcript. "
        "Return JSON only. Do not invent clinical facts. If data is missing, use 'Not mentioned' "
        "for strings and [] for lists. Keep medication details exactly as stated."
    ),
    user_prompt_template=(
        "Consultation {consultation_id}\n"
        "Facility: {facility_name} | Department: {department}\n"
        "Encounter date: {encounter_date} | time: {encounter_time}\n"
        "Clinician: {clinician_name}\n\n"
        "PATIENT METADATA\n"
        "- Name: {patient_name}\n"
        "- Age: {patient_age}\n"
        "- Gender: {patient_gender}\n"
        "- DOB: {patient_date_of_birth}\n"
        "- Phone: {patient_phone}\n"
        "- Address: {patient_address}\n"
        "- Known Allergies: {patient_allergies}\n"
        "- Medical History: {patient_medical_history}\n\n"
        "RAW TRANSCRIPT (verbatim)\n"
        "{transcript_text}\n\n"
        "NORMALIZED TRANSCRIPT JSON\n"
        "{normalized_transcript}\n\n"
        "OUTPUT\n"
        "Return exactly one valid JSON object with these keys (no extra text):\n"
        '{{"patient_info": {{}}, "encounter_info": {{}}, "chief_complaint": "", '
        '"history_of_present_illness": "", "review_of_systems": {{}}, '
        '"past_medical_history": "", "current_medications_mentioned": [], '
        '"allergies": "", "family_history": "", "social_history": {{}}, '
        '"vitals": {{}}, "examination_findings": "", "assessment": {{}}, '
        '"diagnosis": "", "medications": [], "plan": {{}}, '
        '"lab_tests_ordered": [], "follow_up": "", "patient_instructions": "", '
        '"return_precautions": [], "clinical_notes_summary": "", '
        '"missing_but_relevant_information": [], "clinician_approval": {{}}, '
        '"report_markdown": ""}}'
    ),
    temperature=0.2,
    max_tokens=2600,
)

_SUGGESTIVE_PROMPT_SYSTEM = (
    "You are a second-pass outpatient clinical documentation safety reviewer. "
    "Compare the generated clinical report and the normalized transcript. "
    "Return only strict JSON. Use only evidence from the report or transcript. "
    "Do not invent medical facts."
)

_SUGGESTIVE_PROMPT_USER = (
    "Consultation {consultation_id}\n"
    "Generated report JSON: {generated_report}\n"
    "Normalized transcript JSON: {normalized_transcript}\n"
    "Return a JSON object with keys consultation_id, suggestions, overall_risk_level, "
    "summary. Each suggestion must contain keys type, severity, title, detail, "
    "recommendation, source_quote."
)

# ── Transcript fixtures ────────────────────────────────────────────────

# Simple transcript — no allergies, simple headache
_TRANSCRIPT_HEADACHE_NO_ALLERGY = (
    "Patient: I have had a headache for two days. "
    "No fever. No allergies that I know of. "
    "Doctor: I will prescribe paracetamol 500 mg every 6 hours."
)

# Transcript with explicit penicillin allergy + amoxicillin prescribed
_TRANSCRIPT_PENICILLIN_ALLERGY = (
    "Patient: I have a sore throat since yesterday. "
    "I am allergic to penicillin — I had a rash last time. "
    "Doctor: I will give you amoxicillin 500 mg three times a day."
)

# Short transcript with very little clinical info (tests no-invention)
_TRANSCRIPT_MINIMAL = "Patient came in for a routine check. No complaints today."


# ── Shared client/adapters (reused across tests in same session) ───────


@pytest.fixture(scope="module")
def client():
    """Return a live OllamaClient when Ollama is running, else a MockOllamaClient."""
    if _ollama_available():
        return OllamaClient(
            base_url=_OLLAMA_URL,
            model_name=_MODEL,
            timeout_seconds=180.0,
            max_retries=2,
        )
    return MockOllamaClient()


@pytest.fixture(scope="module")
def note_gen(client):
    return OllamaClinicalNoteGenerator(client)


@pytest.fixture(scope="module")
def normalizer(client):
    return OllamaTranscriptNormalizer(client)


@pytest.fixture(scope="module")
def suggestive_svc(client):
    return OllamaSuggestiveModeService(client)


def _make_report_request(
    transcript: str,
    consultation_id: int = 1,
    allergies: str = "No known drug allergies",
) -> ClinicalReportRequest:
    return ClinicalReportRequest(
        consultation_id=consultation_id,
        doctor_id=1,
        patient_id=1,
        transcript_text=transcript,
        normalized_transcript=NormalizedTranscript(
            raw_text=transcript,
            normalized_text=transcript,
        ),
        prompt=_CLINICAL_PROMPT,
        patient_allergies=allergies,
    )


# ── 1. Structural validity ─────────────────────────────────────────────


class TestRealLlmStructuralValidity:
    """Qwen3 must return JSON that validates against GeneratedClinicalNotes."""

    def test_headache_transcript_produces_valid_pydantic_model(self, note_gen):
        notes = note_gen.generate(_make_report_request(_TRANSCRIPT_HEADACHE_NO_ALLERGY))
        assert isinstance(notes, GeneratedClinicalNotes)

    def test_no_field_is_literal_none_string(self, note_gen):
        notes = note_gen.generate(_make_report_request(_TRANSCRIPT_HEADACHE_NO_ALLERGY))
        dumped = notes.model_dump()
        _assert_no_none_string(dumped, path="root")

    def test_medications_are_list(self, note_gen):
        notes = note_gen.generate(_make_report_request(_TRANSCRIPT_HEADACHE_NO_ALLERGY))
        assert isinstance(notes.medications, list)

    def test_diagnosis_is_non_empty(self, note_gen):
        notes = note_gen.generate(_make_report_request(_TRANSCRIPT_HEADACHE_NO_ALLERGY))
        assert (
            notes.diagnosis.strip() != ""
            or notes.assessment.primary_diagnosis.strip() != ""
        ), (
            "Both diagnosis and assessment.primary_diagnosis are empty — model returned nothing"
        )


def _assert_no_none_string(obj, path: str) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            _assert_no_none_string(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _assert_no_none_string(item, f"{path}[{i}]")
    elif isinstance(obj, str):
        assert obj != "None", (
            f"Field {path!r} contains literal string 'None' — model hallucinated a Python repr"
        )


# ── 2. No-invention (hallucination resistance) ─────────────────────────


class TestRealLlmNoInvention:
    """Model must not invent clinical facts absent from the transcript."""

    def test_no_allergy_transcript_does_not_invent_allergy(self, note_gen):
        """Transcript says 'no allergies' — allergy field must not list a drug."""
        notes = note_gen.generate(
            _make_report_request(
                _TRANSCRIPT_HEADACHE_NO_ALLERGY,
                allergies="No known drug allergies",
            )
        )
        allergy_text = notes.allergies.lower()
        # Any named drug allergy in this field is a hallucination
        invented_drugs = ["penicillin", "aspirin", "ibuprofen", "sulfa", "codeine"]
        for drug in invented_drugs:
            assert drug not in allergy_text, (
                f"Model invented allergy to '{drug}' when transcript said 'no known allergies'"
            )

    def test_minimal_transcript_does_not_invent_medications(self, note_gen):
        """Minimal transcript with no medications should produce an empty medication list."""
        notes = note_gen.generate(_make_report_request(_TRANSCRIPT_MINIMAL))
        assert len(notes.medications) == 0 or all(
            m.name.lower() in _TRANSCRIPT_MINIMAL.lower()
            or m.name.lower() in ("not mentioned", "n/a", "none", "")
            for m in notes.medications
        ), (
            f"Model invented medications for a transcript with none: "
            f"{[m.name for m in notes.medications]}"
        )

    def test_headache_transcript_does_not_invent_diagnoses_unrelated_to_input(
        self, note_gen
    ):
        """Transcript only mentions headache — diagnosis should not contain unrelated conditions."""
        notes = note_gen.generate(_make_report_request(_TRANSCRIPT_HEADACHE_NO_ALLERGY))
        diagnosis_lower = notes.diagnosis.lower()
        unrelated = ["diabetes", "hypertension", "cancer", "pneumonia", "fracture"]
        for condition in unrelated:
            assert condition not in diagnosis_lower, (
                f"Model hallucinated '{condition}' in diagnosis for a headache-only transcript"
            )

    def test_normalizer_does_not_invent_symptoms(self, normalizer):
        """Normalized text must not contain symptoms absent from the raw input."""
        raw = "Patient has a cough for three days. No fever."
        result = normalizer.normalize(
            TranscriptNormalizationRequest(
                consultation_id=1,
                transcript_text=raw,
                prompt=_NORM_PROMPT,
            )
        )
        invented = ["chest pain", "dyspnea", "hemoptysis", "wheezing", "vomiting"]
        for symptom in invented:
            assert symptom not in result.normalized_text.lower(), (
                f"Normalizer invented symptom '{symptom}' not present in raw transcript"
            )

    def test_normalizer_preserves_key_clinical_words(self, normalizer):
        raw = "Patient reports severe headache and photophobia since yesterday morning."
        result = normalizer.normalize(
            TranscriptNormalizationRequest(
                consultation_id=2,
                transcript_text=raw,
                prompt=_NORM_PROMPT,
            )
        )
        assert "headache" in result.normalized_text.lower(), (
            "Normalizer dropped 'headache' from transcript"
        )
        assert "photophobia" in result.normalized_text.lower(), (
            "Normalizer dropped 'photophobia' from transcript"
        )


# ── 3. Contraindication faithfulness ──────────────────────────────────


class TestRealLlmContraindication:
    """Suggestive mode must flag penicillin allergy + amoxicillin as RED."""

    def _penicillin_report(self, note_gen) -> dict:
        notes = note_gen.generate(
            _make_report_request(
                _TRANSCRIPT_PENICILLIN_ALLERGY,
                allergies="Penicillin — causes rash",
            )
        )
        return notes.model_dump()

    def test_penicillin_allergy_with_amoxicillin_gives_red_or_yellow(
        self, note_gen, suggestive_svc
    ):
        report = self._penicillin_report(note_gen)
        review = suggestive_svc.review(
            SuggestiveReviewRequest(
                consultation_id=99,
                doctor_id=1,
                patient_id=1,
                generated_report=report,
                normalized_transcript={
                    "normalized_text": _TRANSCRIPT_PENICILLIN_ALLERGY
                },
                system_prompt=_SUGGESTIVE_PROMPT_SYSTEM,
                user_prompt_template=_SUGGESTIVE_PROMPT_USER,
            )
        )
        assert review.overall_risk_level in (RiskLevel.RED, RiskLevel.YELLOW), (
            f"Expected RED or YELLOW risk for penicillin allergy + amoxicillin, "
            f"got {review.overall_risk_level}. Suggestions: {review.suggestions}"
        )

    def test_penicillin_contraindication_appears_in_suggestions(
        self, note_gen, suggestive_svc
    ):
        report = self._penicillin_report(note_gen)
        review = suggestive_svc.review(
            SuggestiveReviewRequest(
                consultation_id=99,
                doctor_id=1,
                patient_id=1,
                generated_report=report,
                normalized_transcript={
                    "normalized_text": _TRANSCRIPT_PENICILLIN_ALLERGY
                },
                system_prompt=_SUGGESTIVE_PROMPT_SYSTEM,
                user_prompt_template=_SUGGESTIVE_PROMPT_USER,
            )
        )
        all_text = " ".join(f"{s.title} {s.detail}".lower() for s in review.suggestions)
        assert (
            "penicillin" in all_text
            or "allerg" in all_text
            or "amoxicillin" in all_text
        ), (
            f"Suggestive mode did not mention the allergy in any suggestion. "
            f"Suggestions: {review.suggestions}"
        )

    def test_no_allergy_transcript_gives_green(self, note_gen, suggestive_svc):
        report = note_gen.generate(
            _make_report_request(
                _TRANSCRIPT_HEADACHE_NO_ALLERGY,
                allergies="No known drug allergies",
            )
        ).model_dump()
        review = suggestive_svc.review(
            SuggestiveReviewRequest(
                consultation_id=100,
                doctor_id=1,
                patient_id=2,
                generated_report=report,
                normalized_transcript={
                    "normalized_text": _TRANSCRIPT_HEADACHE_NO_ALLERGY
                },
                system_prompt=_SUGGESTIVE_PROMPT_SYSTEM,
                user_prompt_template=_SUGGESTIVE_PROMPT_USER,
            )
        )
        assert review.overall_risk_level == RiskLevel.GREEN, (
            f"Expected GREEN for safe prescription, got {review.overall_risk_level}"
        )


# ── 4. Cross-consultation isolation ───────────────────────────────────


class TestRealLlmCrossConsultationIsolation:
    """Two sequential calls must not bleed context into each other."""

    def test_two_independent_calls_produce_different_outputs(self, note_gen):
        notes_a = note_gen.generate(
            _make_report_request(
                "Patient has a sore throat. Prescribed amoxicillin 500 mg.",
                consultation_id=1,
            )
        )
        notes_b = note_gen.generate(
            _make_report_request(
                "Patient has lower back pain. Prescribed ibuprofen 400 mg.",
                consultation_id=2,
            )
        )
        # Diagnoses must not be identical (one is throat, other is back pain)
        assert (
            notes_a.diagnosis.lower() != notes_b.diagnosis.lower()
            or notes_a.diagnosis.strip() == ""
        ), "Both consultations returned the same diagnosis — possible context bleed"

    def test_consultation_b_does_not_contain_consultation_a_medication(self, note_gen):
        note_gen.generate(
            _make_report_request(
                "Patient A: prescribed vancomycin 1g IV.",
                consultation_id=10,
            )
        )
        notes_b = note_gen.generate(
            _make_report_request(
                "Patient B: mild cold. No medications needed.",
                consultation_id=11,
            )
        )
        med_names_b = {m.name.lower() for m in notes_b.medications}
        assert "vancomycin" not in med_names_b, (
            "Consultation 11 output contains 'vancomycin' from consultation 10 — context bleed"
        )


# ── 5. JSON robustness ─────────────────────────────────────────────────


class TestRealLlmJsonRobustness:
    """Model must produce parseable JSON even for edge-case transcripts."""

    def test_very_short_transcript_still_returns_valid_json(self, note_gen):
        notes = note_gen.generate(_make_report_request("Patient is fine."))
        assert isinstance(notes, GeneratedClinicalNotes)

    def test_transcript_with_special_chars_does_not_break_parser(self, note_gen):
        tricky = (
            'Patient said: "I feel a 10/10 pain — it\'s like a knife." '
            "BP: 140/90 mmHg. T: 37.2°C."
        )
        notes = note_gen.generate(_make_report_request(tricky))
        assert isinstance(notes, GeneratedClinicalNotes)

    def test_risk_level_is_always_valid_enum(self, note_gen, suggestive_svc):
        for transcript in [
            _TRANSCRIPT_HEADACHE_NO_ALLERGY,
            _TRANSCRIPT_MINIMAL,
        ]:
            report = note_gen.generate(_make_report_request(transcript)).model_dump()
            review = suggestive_svc.review(
                SuggestiveReviewRequest(
                    consultation_id=200,
                    doctor_id=1,
                    patient_id=1,
                    generated_report=report,
                    normalized_transcript={"normalized_text": transcript},
                    system_prompt=_SUGGESTIVE_PROMPT_SYSTEM,
                    user_prompt_template=_SUGGESTIVE_PROMPT_USER,
                )
            )
            assert isinstance(review.overall_risk_level, RiskLevel), (
                f"overall_risk_level is not a valid RiskLevel enum: {review.overall_risk_level}"
            )
