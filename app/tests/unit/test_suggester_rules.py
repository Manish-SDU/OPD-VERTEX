"""Unit tests for YAML-based clinical rule evaluation."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from app.application.suggestive_mode.hybrid_suggester import RuleOnlySuggester
from app.domain.ai.schemas import Prescription, PrescriptionItem, SOAPNote


@pytest.fixture
def rules_path(tmp_path: Path) -> Path:
    p = tmp_path / "rules.yaml"
    p.write_text(
        textwrap.dedent("""\
            rules:
              - id: chronic_cough_cxr
                severity: medium
                patient_mentions: ["chronic cough"]
                excluded_if_present: ["chest x-ray"]
                suggestion: "Consider Chest X-Ray."
              - id: chest_pain_ecg
                severity: high
                patient_mentions: ["chest pain"]
                excluded_if_present: ["ecg"]
                suggestion: "Consider ECG."
        """)
    )
    return p


@pytest.mark.asyncio
async def test_rule_fires_when_doctor_missed_it(rules_path: Path):
    s = RuleOnlySuggester(str(rules_path))
    transcript = "Patient reports chronic cough for 4 weeks."
    note = SOAPNote(
        subjective="cough",
        objective="",
        assessment="bronchitis?",
        plan="rest, fluids",
        prescription=Prescription(),
    )
    out = await s.suggest(transcript, note)
    assert any(i.rule_id == "chronic_cough_cxr" for i in out.items)


@pytest.mark.asyncio
async def test_rule_excluded_when_doctor_already_addressed(rules_path: Path):
    s = RuleOnlySuggester(str(rules_path))
    transcript = "Patient reports chronic cough."
    note = SOAPNote(
        subjective="cough",
        objective="",
        assessment="",
        plan="ordered chest x-ray and rest",
        prescription=Prescription(items=[PrescriptionItem(drug="Salbutamol")]),
    )
    out = await s.suggest(transcript, note)
    assert not any(i.rule_id == "chronic_cough_cxr" for i in out.items)


@pytest.mark.asyncio
async def test_no_rules_fire_unrelated_complaint(rules_path: Path):
    s = RuleOnlySuggester(str(rules_path))
    transcript = "Patient reports a sore throat for 2 days."
    note = SOAPNote(
        subjective="sore throat",
        objective="",
        assessment="pharyngitis",
        plan="paracetamol",
        prescription=Prescription(),
    )
    out = await s.suggest(transcript, note)
    assert out.items == []
