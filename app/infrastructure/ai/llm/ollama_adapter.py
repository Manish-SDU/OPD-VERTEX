"""Ollama-backed adapters for transcript normalization and structured review."""

from __future__ import annotations

import json
import re

from app.domain.clinical_notes.models import (
    ClinicalNoteGenerator,
    ClinicalReportRequest,
    GeneratedClinicalNotes,
    LlmHealthStatus,
    LocalLlmHealthService,
    NormalizedTranscript,
    TranscriptNormalizationRequest,
    TranscriptNormalizer,
)
from pydantic import ValidationError

from app.domain.suggestive_mode.models import (
    SuggestiveModeService,
    SuggestiveReview,
    SuggestiveReviewRequest,
)
from app.infrastructure.ai.llm.ollama_client import OllamaClient

_PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _render_prompt(template: str, **values: str) -> str:
    """Replace {simple_name} tokens only — leaves JSON braces in the template untouched."""
    missing = []

    def _sub(m: re.Match) -> str:
        key = m.group(1)
        if key in values:
            return str(values[key])
        missing.append(key)
        return m.group(0)

    result = _PLACEHOLDER.sub(_sub, template)
    if missing:
        raise ValueError(f"Prompt template is missing placeholder: {missing[0]!r}")
    return result


class OllamaTranscriptNormalizer(TranscriptNormalizer):
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    def normalize(
        self, request: TranscriptNormalizationRequest
    ) -> NormalizedTranscript:
        user_prompt = _render_prompt(
            request.prompt.user_prompt_template,
            consultation_id=str(request.consultation_id),
            transcript_text=json.dumps(request.transcript_text),
        )
        payload = self.client.generate_json(
            system_prompt=request.prompt.system_prompt,
            user_prompt=user_prompt,
            temperature=request.prompt.temperature,
            max_tokens=request.prompt.max_tokens,
        )
        return NormalizedTranscript.model_validate(payload)


class OllamaClinicalNoteGenerator(ClinicalNoteGenerator):
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    def generate(self, request: ClinicalReportRequest) -> GeneratedClinicalNotes:
        user_prompt = _render_prompt(
            request.prompt.user_prompt_template,
            consultation_id=str(request.consultation_id),
            doctor_id=str(request.doctor_id),
            patient_id=str(request.patient_id),
            patient_name=request.patient_name,
            patient_age=request.patient_age,
            patient_gender=request.patient_gender,
            patient_date_of_birth=request.patient_date_of_birth,
            patient_phone=request.patient_phone,
            patient_address=request.patient_address,
            patient_allergies=request.patient_allergies,
            patient_medical_history=request.patient_medical_history,
            clinician_name=request.clinician_name,
            facility_name=request.facility_name,
            department=request.department,
            visit_type=request.visit_type,
            consultation_mode=request.consultation_mode,
            encounter_date=request.encounter_date,
            encounter_time=request.encounter_time,
            transcript_text=json.dumps(request.transcript_text),
            normalized_transcript=json.dumps(
                request.normalized_transcript.model_dump(), ensure_ascii=True
            ),
        )
        payload = self.client.generate_json(
            system_prompt=request.prompt.system_prompt,
            user_prompt=user_prompt,
            temperature=request.prompt.temperature,
            max_tokens=request.prompt.max_tokens,
        )
        return GeneratedClinicalNotes.model_validate(payload)


_VALID_TYPES = {"OMISSION", "CONTRAINDICATION", "DOSAGE_CHECK", "STANDARD_OF_CARE", "INTERACTION_WARNING", "FOLLOW_UP"}
_VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
_VALID_RISKS = {"GREEN", "YELLOW", "RED"}


def _coerce_suggestive_output(raw: dict, consultation_id: int) -> dict:
    """Normalise LLM output so small models with wrong enum casing/values still validate."""
    raw.setdefault("consultation_id", consultation_id)
    raw.setdefault("summary", "")
    if not isinstance(raw.get("summary"), str):
        raw["summary"] = ""
    risk = str(raw.get("overall_risk_level", "")).upper()
    raw["overall_risk_level"] = risk if risk in _VALID_RISKS else "GREEN"
    coerced = []
    for s in raw.get("suggestions", []):
        if not isinstance(s, dict):
            continue
        t = str(s.get("type", "")).upper()
        s["type"] = t if t in _VALID_TYPES else "OMISSION"
        sev = str(s.get("severity", "")).upper()
        s["severity"] = sev if sev in _VALID_SEVERITIES else "LOW"
        s.setdefault("source_quote", "N/A")
        coerced.append(s)
    raw["suggestions"] = coerced
    return raw


class OllamaSuggestiveModeService(SuggestiveModeService):
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    def review(self, request: SuggestiveReviewRequest) -> SuggestiveReview:
        user_prompt = _render_prompt(
            request.user_prompt_template,
            consultation_id=str(request.consultation_id),
            doctor_id=str(request.doctor_id),
            patient_id=str(request.patient_id),
            generated_report=json.dumps(request.generated_report, ensure_ascii=True),
            normalized_transcript=json.dumps(
                request.normalized_transcript, ensure_ascii=True
            )
            if request.normalized_transcript is not None
            else "{}",
        )
        payload = self.client.generate_json(
            system_prompt=request.system_prompt,
            user_prompt=user_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        payload = _coerce_suggestive_output(payload, request.consultation_id)
        try:
            return SuggestiveReview.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(
                "Suggestive review returned invalid structured output."
            ) from exc


class OllamaHealthService(LocalLlmHealthService):
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    def check_health(self) -> LlmHealthStatus:
        return self.client.check_status()
