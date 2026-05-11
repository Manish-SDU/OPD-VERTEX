# Testing

## Summary

310 tests — 0 failures — 0 skipped

| Suite | Count | What it covers |
|---|---|---|
| Unit | 263 | Domain models, repos, services, logging, security, PDF, LLM mocks, versioning, hallucination guards |
| Integration | 30 | Full HTTP flows, PDF routes, real-LLM prompts (auto-skip if Ollama offline) |
| Benchmarks | 10 | p50/p95/p99 latency for all hot paths |
| Stress | 14 | 1 000 patient creates, 500 concurrent writes, 50 end-to-end pipeline runs |
| Smoke | 6 | App boots, health endpoints respond |

## Running tests

```bash
# Everything
pytest

# By suite
pytest app/tests/unit/
pytest app/tests/integration/
pytest app/tests/benchmarks/
pytest app/tests/stress/
pytest app/tests/smoke/

# Generate benchmark HTML report → reports/benchmark_report.html
python scripts/generate_test_graphs.py
```

## Real-LLM tests

`app/tests/integration/test_real_llm.py` fires live prompts at Qwen3:8b. They **auto-skip** when Ollama is offline so CI never breaks.

```bash
# Requires: ollama serve + ollama pull qwen3:8b
pytest app/tests/integration/test_real_llm.py -v -s
```

What they verify:

| Class | Tests | Checks |
|---|---|---|
| `TestRealLlmStructuralValidity` | 4 | Pydantic parses response, no `"None"` leaks, medications is a list |
| `TestRealLlmNoInvention` | 5 | No hallucinated allergies/meds, normaliser preserves key terms |
| `TestRealLlmContraindication` | 3 | Penicillin + amoxicillin → RED flag; safe prescription → GREEN |
| `TestRealLlmCrossConsultationIsolation` | 2 | Two calls return different diagnoses, no data bleed |
| `TestRealLlmJsonRobustness` | 3 | Short/special-char transcripts parse; risk level always a valid enum |

## Benchmark results (mock adapters, Python 3.12)

All in-memory — no DB or LLM calls.

| Operation | p50 (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| patient list | 0.001 | 0.001 | 0.003 |
| patient search | 0.002 | 0.002 | 0.005 |
| patient create | 0.005 | 0.007 | 0.032 |
| consultation list | 0.001 | 0.001 | 0.001 |
| consultation create | 0.003 | 0.004 | 0.031 |
| mock report generation | 0.010 | 0.012 | 0.070 |
| transcript normaliser | 0.003 | 0.004 | 0.007 |
| document edit | 0.092 | 0.106 | 0.284 |

Charts: `reports/benchmark_report.html`
