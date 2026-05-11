"""Hybrid clinical suggester: deterministic YAML rules + LLM reasoning, deduplicated."""
from __future__ import annotations

import logging

from app.application.suggestive_mode.clinical_rules import (
    ClinicalRule,
    evaluate_clinical_rules,
    load_clinical_rules,
)
from app.domain.ai.schemas import SOAPNote, Suggestion, SuggesterOutput

log = logging.getLogger(__name__)

_SUGGESTER_SYSTEM = """You are a careful clinical safety-net reviewer for an outpatient clinic.
You will receive: the consultation transcript, the doctor's draft SOAP note,
and the list of deterministic rules that have ALREADY fired.

Your job:
- Surface ADDITIONAL standard-of-care omissions or important investigations
  the deterministic rules missed.
- Be conservative. Quality over quantity. Do NOT repeat anything already
  in the "rules already fired" list.
- Do NOT invent findings not supported by the transcript.
- If you have nothing to add, return {"items": []}.

Return STRICT JSON only, conforming to:
{
  "items": [
    {
      "type": "investigation|medication_check|referral|lifestyle|safety|other",
      "severity": "low|medium|high",
      "message": "<concise clinical reason>",
      "source": "llm"
    }
  ]
}"""


def _rules_to_suggestions(fired: list[ClinicalRule]) -> list[Suggestion]:
    return [
        Suggestion(
            type="investigation",
            severity=r.severity,
            message=r.suggestion,
            source="rule",
            rule_id=r.id,
        )
        for r in fired
    ]


class RuleOnlySuggester:
    """Pure deterministic suggester — no LLM, deterministic and fast."""

    def __init__(self, rules_path: str):
        self.rules = load_clinical_rules(rules_path)

    async def suggest(self, transcript_text: str, note: SOAPNote) -> SuggesterOutput:
        plan_text = (note.plan or "") + " " + " ".join(i.drug for i in note.prescription.items)
        fired = evaluate_clinical_rules(self.rules, transcript_text, plan_text)
        items = _rules_to_suggestions(fired)
        return SuggesterOutput(items=items)


class HybridSuggester:
    """Rules first, then LLM adds omissions not covered by rules, deduplicated."""

    def __init__(self, llm, rules_path: str, llm_temperature: float = 0.3):
        self.llm = llm
        self.rules = load_clinical_rules(rules_path)
        self.temperature = llm_temperature

    async def suggest(self, transcript_text: str, note: SOAPNote) -> SuggesterOutput:
        plan_text = (note.plan or "") + " " + " ".join(i.drug for i in note.prescription.items)
        fired = evaluate_clinical_rules(self.rules, transcript_text, plan_text)
        rule_items = _rules_to_suggestions(fired)

        rules_summary = "\n".join(f"- [{r.id}] {r.suggestion}" for r in fired) or "(none)"
        user = (
            f"Transcript:\n{transcript_text}\n\n"
            f"Doctor SOAP:\n{note.model_dump_json(indent=2)}\n\n"
            f"Rules already fired (do not duplicate):\n{rules_summary}"
        )
        try:
            llm_out: SuggesterOutput = await self.llm.generate_json(
                _SUGGESTER_SYSTEM, user, SuggesterOutput, retries=1, temperature=self.temperature
            )
            for s in llm_out.items:
                s.source = "llm"
                s.rule_id = None
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM suggester failed (%s) — returning rules only", exc)
            llm_out = SuggesterOutput()

        rule_texts = [s.message.lower() for s in rule_items]
        deduped_llm: list[Suggestion] = []
        for s in llm_out.items:
            if not any(rt[:40] in s.message.lower() for rt in rule_texts):
                deduped_llm.append(s)

        return SuggesterOutput(items=rule_items + deduped_llm)
