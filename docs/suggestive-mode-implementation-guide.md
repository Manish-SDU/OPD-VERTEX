# Suggestive Mode Implementation Guide

This document explains how to implement a robust Suggestive Mode in OPD-Vertex.

The goal is to turn the current second-pass review into a clinically useful safety layer that reviews generated drafts before final approval.

## Purpose

Suggestive Mode should act as a structured clinical quality check after report generation and before doctor approval.

It should not replace clinician judgment.

It should:

- highlight possible safety issues
- flag inconsistencies between transcript and generated report
- detect likely omissions
- suggest follow-up improvements
- surface potential medication risks
- help the doctor review faster and more safely

## What Suggestive Mode Should Detect

The implementation should support at least these categories:

### 1. Clinical omissions

Examples:

- allergy discussed in transcript but missing in report
- medication history mentioned but not documented
- important symptoms missing from the assessment
- abnormal vital signs not addressed
- documented red flags not reflected in the plan

### 2. Contraindications

Examples:

- penicillin allergy with amoxicillin prescribed
- known kidney disease with unsafe medication choice
- pregnancy-related contraindications
- asthma history with inappropriate medication suggestion

### 3. Dosage checks

Examples:

- dose missing
- frequency missing
- duration missing
- dosage obviously unusual for a common medication
- unit mismatch or malformed regimen

Important note:

The first version should focus on heuristic validation and “possible issue” wording, not claim authoritative pharmacology unless a reliable reference source is integrated.

### 4. Interaction warnings

Examples:

- multiple medications that may interact
- duplicate therapeutic intent
- documented home medication conflicts with newly proposed medication

Again, first iteration may use lightweight rule-based checks before introducing a full drug interaction knowledge source.

### 5. Missing or weak follow-up

Examples:

- no follow-up plan provided
- follow-up interval too vague
- no escalation guidance for potentially unstable conditions
- return precautions missing for risky presentations

### 6. Standard-of-care concerns

Examples:

- likely bacterial infection without clear treatment rationale
- abnormal findings with no workup plan
- persistent fatigue without basic laboratory workup
- concerning symptom cluster with no escalation advice

This category should be framed carefully as:

- “possible review point”
- “consider clarifying”
- “may warrant reassessment”

not as definitive legal or clinical claims.

## Suggested Product Behavior

When a doctor clicks `Run Suggestive Review`, the system should:

1. Load the generated draft
2. Load the normalized transcript
3. Load relevant source context
4. Run a second-pass review prompt
5. Produce structured suggestions
6. Store the result
7. Show it inside the review page before approval

## Current Data Flow

Today the route is:

- `POST /review/{consultation_id}/suggestive-review`

The service is:

- `app/application/suggestive_mode/services.py`

The current prompt id is:

- `suggestive_mode_v2`

The models live in:

- `app/domain/suggestive_mode/models.py`

This is already the right architecture for a real implementation.

## Recommended Input Context for Suggestive Review

The second-pass review should not look only at the generated report.

It should receive:

### Required inputs

- generated clinical report JSON
- normalized transcript JSON
- consultation id
- patient id
- doctor id

### Recommended additional inputs

- patient demographics
- known allergies
- current medications
- past medical history
- vital signs
- original transcript excerpt if needed

### Optional future inputs

- medication knowledge base
- clinical rules library
- local formulary constraints
- safety guideline snippets

## Recommended Output Shape

Keep the existing structured schema and expand usage consistently.

The current model already supports:

- `consultation_id`
- `suggestions`
- `overall_risk_level`
- `summary`

Each suggestion should include:

- `type`
- `severity`
- `title`
- `detail`
- `recommendation`
- `source_quote`

This is good and should be preserved.

## Suggested Severity Semantics

Use severity consistently:

- `LOW`
  formatting gaps, minor missing detail, helpful clarification
- `MEDIUM`
  clinically relevant omission or plan weakness
- `HIGH`
  likely significant safety risk or strong inconsistency
- `CRITICAL`
  likely contraindication or high-risk issue needing immediate correction

Suggested overall risk mapping:

- `GREEN`
  no major issues, minor or no suggestions
- `YELLOW`
  at least one medium or high concern
- `RED`
  at least one critical concern

## Where the Prompt Should Live

Store the prompt in the same prompt management flow already used elsewhere.

Recommended location:

- prompt source file:
  `app/prompts/suggestive_mode_v3.md`

Then seed it into MongoDB through the existing prompt bootstrap path.

Relevant files:

- `app/infrastructure/bootstrap/prompt_seed.py`
- `app/infrastructure/bootstrap/startup.py`
- `app/infrastructure/db/mongo/repositories/mongo_repos.py`

If you keep versioning explicit, add:

- prompt id: `suggestive_mode_v3`

and update:

- `SUGGESTIVE_REVIEW_PROMPT_ID` in
  `app/application/suggestive_mode/services.py`

## Recommended Prompt Design

The prompt should clearly instruct the model to:

- compare transcript and report
- identify specific categories of review findings
- avoid hallucinating unsupported medical facts
- return only strict JSON
- quote the supporting source evidence
- distinguish missing information from true contradictions

### Prompt sections to include

1. System role
   Example:
   - “You are a second-pass outpatient clinical documentation safety reviewer.”

2. Review goals
   Explicitly list:
   - omissions
   - contraindications
   - dosage concerns
   - interaction concerns
   - missing follow-up
   - standard-of-care concerns

3. Grounding rules
   Example:
   - do not invent medical facts
   - if uncertain, downgrade confidence and flag as review-needed
   - use only transcript/report evidence
   - do not rewrite the report

4. Output contract
   Force JSON matching the existing `SuggestiveReview` structure

5. Severity rules
   Provide concrete thresholds

6. Source quote requirement
   Require a quote or source excerpt from transcript/report evidence whenever possible

## Suggested Prompt File Structure

Recommended new file:

- `app/prompts/suggestive_mode_v3.md`

Suggested contents:

- purpose and reviewer role
- allowed finding categories
- severity rubric
- grounding rules
- JSON schema
- example input/output

## Prompt Seeding

Add the new prompt to:

- `app/infrastructure/bootstrap/prompt_seed.py`

Make sure the seeded document includes:

- `id`
- `prompt_name`
- `version`
- `model_target`
- `system_prompt`
- `user_prompt_template`
- `temperature`
- `max_tokens`

Then either:

- enable seeding on startup

or

- run the prompt seed flow manually

## Recommended Implementation Layers

### 1. Domain layer

Keep the current models in:

- `app/domain/suggestive_mode/models.py`

Possible future improvements:

- add confidence score
- add field path or section path
- add recommendation priority

### 2. Application layer

Main orchestration already exists in:

- `app/application/suggestive_mode/services.py`

Enhance it to:

- load more complete context
- support prompt version upgrades
- support regenerate behavior cleanly
- optionally merge rule-based and LLM-based findings

### 3. Infrastructure layer

Current implementation:

- `app/infrastructure/ai/llm/ollama_adapter.py`

or mock equivalent

Enhance the real adapter to:

- pass structured payloads cleanly
- validate JSON response
- tolerate minor malformed outputs
- log raw excerpts safely

## Recommended Hybrid Design

The best real implementation is not “LLM only”.

Use a hybrid pipeline:

### Stage 1: Deterministic rule checks

Rule-based checks for:

- allergy-medication conflicts
- missing medication dose/frequency/duration
- missing follow-up
- empty return precautions
- report/transcript field mismatch for known key items

### Stage 2: LLM suggestive review

LLM reviews:

- nuanced omissions
- contextual standard-of-care gaps
- prioritization of findings
- natural-language recommendations

### Stage 3: Merge findings

Combine rule-based findings and LLM findings into one output object.

Benefits:

- safer
- more explainable
- more stable
- less hallucination-prone

## Recommended Rule Engine Targets

Good first deterministic checks:

- allergies vs prescribed medications
- duplicated medications
- diagnosis present but no plan
- abnormal vitals with no assessment mention
- no follow-up for unresolved condition
- no patient instructions
- no return precautions for medium/high-risk complaint

These can live in a helper module such as:

- `app/application/suggestive_mode/rules.py`

or

- `app/infrastructure/clinical_rules/suggestive_checks.py`

## UI Recommendations

On the review page, suggestions should be clearly grouped and visible.

Recommended UI improvements:

- color by severity
- badge for risk level
- group by suggestion type
- show `source_quote`
- show quick recommendation
- allow doctor to dismiss or acknowledge a suggestion

Possible future features:

- “mark as addressed”
- “copy recommendation into report editor”
- “regenerate after edits”

## Suggested Endpoint Contract

Keep:

- `POST /review/{consultation_id}/suggestive-review`

Optional additions:

- `POST /review/{consultation_id}/suggestive-review/regenerate`
- `GET /review/{consultation_id}/suggestive-review`

## Error Handling

Return controlled errors when:

- consultation does not exist
- generated report is missing
- prompt is missing
- model response is invalid

Recommended messages:

- `Consultation {id} does not have a generated draft yet.`
- `Prompt 'suggestive_mode_v3' is missing from llm_prompts.`
- `Suggestive review returned invalid structured output.`

## Logging Recommendations

Log:

- consultation id
- prompt id/version
- model name
- number of findings
- risk level
- parse/validation failures

Do not log full PHI-heavy payloads unless explicitly redacted.

## Testing Plan

### Unit tests

Add tests for:

- allergy contradiction detection
- missing follow-up detection
- missing dosage detection
- missing return precautions
- fatigue workup gap
- empty report behavior

### Integration tests

Test:

- route returns structured JSON
- stored suggestive output is persisted
- review page renders suggestions
- regenerate path replaces previous suggestions

### Manual scenario set

Prepare explicit seed cases:

- allergy conflict case
- dehydration/orthostasis case
- incomplete fatigue workup case
- normal low-risk case

## Suggested Seed Cases

The current seeded consultations already map well:

- `4101`
  low-risk uncomplicated pharyngitis
- `4102`
  orthostatic dizziness/dehydration
- `4103`
  allergy/antibiotic safety case
- `4104`
  fatigue with incomplete background data

These should become the canonical demo set for Suggestive Mode validation.

## Recommended Delivery Plan

### Phase 1

- add `suggestive_mode_v3.md`
- improve real prompt content
- improve mock output realism
- improve UI rendering

### Phase 2

- add deterministic rule checks
- merge rule and LLM findings
- improve source quoting

### Phase 3

- add clinician acknowledgment workflow
- add persistence of addressed findings
- add audit trail for review actions

## Recommended First Practical Step

The best next implementation step is:

1. create `app/prompts/suggestive_mode_v3.md`
2. update prompt seeding
3. add a small deterministic rules module
4. merge those findings with the LLM review output
5. render suggestions more clearly in the review UI

That gives a Suggestive Mode that is safer, more explainable, and much more credible for demos and real workflows.
