"""YAML-based clinical rule loader and evaluator for the new hybrid suggester."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class ClinicalRule:
    id: str
    severity: str
    patient_mentions: list[str]
    excluded_if_present: list[str]
    suggestion: str


def load_clinical_rules(path: str | Path) -> list[ClinicalRule]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open() as f:
        raw = yaml.safe_load(f) or {}
    out: list[ClinicalRule] = []
    for r in raw.get("rules", []):
        out.append(ClinicalRule(
            id=r["id"],
            severity=r.get("severity", "low"),
            patient_mentions=[s.lower() for s in r.get("patient_mentions", [])],
            excluded_if_present=[s.lower() for s in r.get("excluded_if_present", [])],
            suggestion=r["suggestion"],
        ))
    return out


def evaluate_clinical_rules(
    rules: list[ClinicalRule], transcript_text: str, plan_text: str
) -> list[ClinicalRule]:
    """Return rules that fire: triggered by transcript AND not already addressed in plan."""
    t = transcript_text.lower()
    p = plan_text.lower()
    fired: list[ClinicalRule] = []
    for r in rules:
        if not any(m in t for m in r.patient_mentions):
            continue
        if r.excluded_if_present and any(e in p for e in r.excluded_if_present):
            continue
        fired.append(r)
    return fired
