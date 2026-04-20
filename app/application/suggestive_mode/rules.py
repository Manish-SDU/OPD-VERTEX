"""Deterministic suggestive review checks for safety and completeness."""

from __future__ import annotations

import re
from typing import Any

from app.domain.suggestive_mode.models import (
    RiskLevel,
    Suggestion,
    SuggestionSeverity,
    SuggestionType,
    SuggestiveReview,
)

_MEDICATION_MISSING_FIELDS = {
    "dosage": "dose",
    "frequency": "frequency",
    "duration": "duration",
}

_MEDICATION_CONTRAINDICATIONS = {
    "penicillin": [
        "amoxicillin",
        "ampicillin",
        "amoxicillin/clavulanate",
        "penicillin",
    ],
    "sulfa": ["sulfamethoxazole", "sulfa", "sulfasalazine"],
    "aspirin": ["aspirin", "ibuprofen", "naproxen"],
}


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _contains_text(value: Any, needle: str) -> bool:
    return needle.strip().lower() in _normalize_text(value)


def _split_terms(value: Any) -> list[str]:
    text = _normalize_text(value)
    if not text:
        return []
    return [term.strip() for term in re.split(r"[,;\n]", text) if term.strip()]


def _extract_medications(generated_report: dict[str, Any]) -> list[dict[str, str]]:
    medications = generated_report.get("medications", [])
    if not isinstance(medications, list):
        return []

    extracted: list[dict[str, str]] = []
    for medication in medications:
        if not isinstance(medication, dict):
            continue
        extracted.append(
            {
                "name": _normalize_text(medication.get("name", "")),
                "dosage": _normalize_text(medication.get("dosage", "")),
                "frequency": _normalize_text(medication.get("frequency", "")),
                "duration": _normalize_text(medication.get("duration", "")),
                "route": _normalize_text(medication.get("route", "")),
            }
        )
    return extracted


def _extract_allergies(generated_report: dict[str, Any]) -> list[str]:
    allergies = generated_report.get("allergies", "")
    return _split_terms(allergies)


def _compute_risk_level(suggestions: list[Suggestion]) -> RiskLevel:
    if any(item.severity == SuggestionSeverity.CRITICAL for item in suggestions):
        return RiskLevel.RED
    if any(
        item.severity in (SuggestionSeverity.HIGH, SuggestionSeverity.MEDIUM)
        for item in suggestions
    ):
        return RiskLevel.YELLOW
    return RiskLevel.GREEN


def _build_source_quote(candidate: str, fallback: str) -> str:
    text = _normalize_text(candidate)
    if not text:
        return fallback
    return fallback if fallback == "N/A" else fallback


def build_deterministic_suggestions(
    generated_report: dict[str, Any],
    normalized_transcript: dict[str, Any] | None = None,
) -> list[Suggestion]:
    suggestions: list[Suggestion] = []
    medications = _extract_medications(generated_report)
    allergies = _extract_allergies(generated_report)
    diagnosis = _normalize_text(generated_report.get("diagnosis", ""))
    follow_up = _normalize_text(generated_report.get("follow_up", ""))
    patient_instructions = _normalize_text(
        generated_report.get("patient_instructions", "")
    )
    return_precautions = generated_report.get("return_precautions", [])
    plan = generated_report.get("plan", {})
    plan_missing = isinstance(plan, dict) and not any(
        _normalize_text(value) if isinstance(value, str) else bool(value)
        for value in plan.values()
    )
    transcript_blob = (
        _normalize_text(normalized_transcript)
        if normalized_transcript is not None
        else ""
    )

    if allergies and medications:
        for allergy in allergies:
            for term, contraindicated_drugs in _MEDICATION_CONTRAINDICATIONS.items():
                if term in allergy:
                    for drug in contraindicated_drugs:
                        if any(drug in med["name"] for med in medications):
                            suggestions.append(
                                Suggestion(
                                    type=SuggestionType.CONTRAINDICATION,
                                    severity=SuggestionSeverity.CRITICAL,
                                    title=f"Possible {term.capitalize()} allergy contraindication",
                                    detail=(
                                        f"The report documents a {allergy} allergy while the medication list includes {drug}."
                                    ),
                                    recommendation=(
                                        "Confirm the allergy and choose a safer alternative medication before approval."
                                    ),
                                    source_quote=(
                                        f"Allergy: {allergy}; medication: {drug}"
                                    ),
                                )
                            )
                            break

    duplicates: dict[str, int] = {}
    for med in medications:
        if not med["name"]:
            continue
        duplicates[med["name"]] = duplicates.get(med["name"], 0) + 1
    for med_name, count in duplicates.items():
        if count > 1:
            suggestions.append(
                Suggestion(
                    type=SuggestionType.INTERACTION_WARNING,
                    severity=SuggestionSeverity.MEDIUM,
                    title="Duplicate medication entry detected",
                    detail=(
                        f"The generated report includes {count} entries for {med_name}. "
                        "Duplicate therapy can increase risk and should be reviewed."
                    ),
                    recommendation=(
                        "Review the medication list and consolidate or clarify duplicate entries."
                    ),
                    source_quote=f"Medication repeated: {med_name}",
                )
            )

    for med in medications:
        missing_fields = [
            label
            for field, label in _MEDICATION_MISSING_FIELDS.items()
            if not med[field]
        ]
        if missing_fields:
            suggestions.append(
                Suggestion(
                    type=SuggestionType.DOSAGE_CHECK,
                    severity=SuggestionSeverity.MEDIUM,
                    title="Incomplete medication instructions detected",
                    detail=(
                        f"The medication '{med['name']}' is missing {', '.join(missing_fields)} in the generated report."
                    ),
                    recommendation=(
                        "Add the missing dosage, frequency, or duration information before approval."
                    ),
                    source_quote=(
                        f"Medication '{med['name']}' missing {', '.join(missing_fields)}"
                    ),
                )
            )

    if diagnosis and plan_missing:
        suggestions.append(
            Suggestion(
                type=SuggestionType.STANDARD_OF_CARE,
                severity=SuggestionSeverity.MEDIUM,
                title="Diagnosis present without actionable plan details",
                detail=(
                    "The report has a documented diagnosis but the care plan is incomplete or empty."
                ),
                recommendation=(
                    "Add plan details, follow-up instructions, or testing/referrals to support the diagnosis."
                ),
                source_quote="Diagnosis present with no clear clinical plan.",
            )
        )

    if diagnosis and not follow_up and not patient_instructions:
        suggestions.append(
            Suggestion(
                type=SuggestionType.FOLLOW_UP,
                severity=SuggestionSeverity.MEDIUM,
                title="Follow-up and patient instruction plan is missing",
                detail=(
                    "The report documents a diagnosis but does not specify follow-up or patient instructions."
                ),
                recommendation=(
                    "Document the recommended follow-up interval and any patient self-care instructions."
                ),
                source_quote="Missing follow-up and patient instructions.",
            )
        )

    if (
        transcript_blob
        and "return precautions" in transcript_blob
        and not return_precautions
    ):
        suggestions.append(
            Suggestion(
                type=SuggestionType.STANDARD_OF_CARE,
                severity=SuggestionSeverity.LOW,
                title="Return precautions are not documented",
                detail=(
                    "The transcript mentions return precautions, but the report does not include them."
                ),
                recommendation=(
                    "Add explicit return precautions and escalation guidance to the report."
                ),
                source_quote="Transcript mentions return precautions.",
            )
        )

    if transcript_blob and "follow up" in transcript_blob and not follow_up:
        suggestions.append(
            Suggestion(
                type=SuggestionType.FOLLOW_UP,
                severity=SuggestionSeverity.MEDIUM,
                title="Follow-up plan referenced in transcript but missing in report",
                detail=(
                    "The transcript appears to discuss follow-up, but the structured report does not include a follow-up plan."
                ),
                recommendation=(
                    "Confirm whether follow-up instructions were intended and add them to the report if needed."
                ),
                source_quote="Transcript mentions follow up.",
            )
        )

    return suggestions


def merge_suggestive_reviews(
    review: SuggestiveReview, supplemental: list[Suggestion]
) -> SuggestiveReview:
    if not supplemental:
        return review

    existing_by_title: dict[str, Suggestion] = {
        suggestion.title.strip().lower(): suggestion
        for suggestion in review.suggestions
    }

    severity_order = {
        SuggestionSeverity.LOW: 0,
        SuggestionSeverity.MEDIUM: 1,
        SuggestionSeverity.HIGH: 2,
        SuggestionSeverity.CRITICAL: 3,
    }

    for suggestion in supplemental:
        key = suggestion.title.strip().lower()
        if key in existing_by_title:
            existing = existing_by_title[key]
            if severity_order[suggestion.severity] > severity_order[existing.severity]:
                existing.severity = suggestion.severity
            if not existing.detail:
                existing.detail = suggestion.detail
            if not existing.recommendation:
                existing.recommendation = suggestion.recommendation
            if not existing.source_quote:
                existing.source_quote = suggestion.source_quote
        else:
            review.suggestions.append(suggestion)

    review.overall_risk_level = _compute_risk_level(review.suggestions)
    if not review.summary:
        review.summary = f"{len(review.suggestions)} issue(s) flagged for clinician review before approval."
    return review
