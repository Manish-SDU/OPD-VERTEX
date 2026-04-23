"""Performance benchmarks for core application operations.

These tests measure wall-clock latency for the critical hot paths and
record the results so the graph-generation script can render charts.
Each test asserts that the measured time stays under a reasonable
threshold for in-memory (mock) adapters.

Results are written to ``reports/benchmark_results.json`` so that
``scripts/generate_test_graphs.py`` can consume them without re-running
all benchmarks.
"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import Callable

from app.application.clinical_notes.editing import DocumentEditingService
from app.application.consultations.services import ConsultationApplicationService
from app.application.patients.services import PatientApplicationService
from app.domain.clinical_notes.models import (
    ClinicalReportRequest,
    LlmPromptConfig,
    NormalizedTranscript,
)
from app.domain.consultations.models import ConsultationCreateRequest
from app.domain.patients.models import PatientCreateRequest
from app.infrastructure.persistence.in_memory.repositories import (
    InMemoryConsultationDocumentRepository,
    InMemoryConsultationRepository,
    InMemoryGeneratedDocumentRepository,
    InMemoryPatientRepository,
    MockClinicalNoteGenerator,
    MockTranscriptNormalizer,
)

# ── Helpers ────────────────────────────────────────────────────────────

REPORT_DIR = Path(__file__).resolve().parents[3] / "reports"


def _time_fn(fn: Callable, iterations: int = 100) -> dict:
    """Run *fn* *iterations* times and return timing statistics (ms)."""
    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        times.append((time.perf_counter() - start) * 1000)

    times.sort()
    n = len(times)
    mean = sum(times) / n
    p50 = times[n // 2]
    p95 = times[int(n * 0.95)]
    p99 = times[int(n * 0.99)]
    return {
        "iterations": n,
        "mean_ms": round(mean, 3),
        "p50_ms": round(p50, 3),
        "p95_ms": round(p95, 3),
        "p99_ms": round(p99, 3),
        "min_ms": round(times[0], 3),
        "max_ms": round(times[-1], 3),
    }


def _save_result(label: str, stats: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / "benchmark_results.json"
    results: dict = {}
    if path.exists():
        results = json.loads(path.read_text())
    results[label] = stats
    path.write_text(json.dumps(results, indent=2))


# ── Patient service benchmarks ─────────────────────────────────────────


class TestPatientServicePerf:
    def test_list_patients_under_5ms_p99(self):
        repo = InMemoryPatientRepository()
        svc = PatientApplicationService(repo)

        stats = _time_fn(svc.list_patients, iterations=200)
        _save_result("patient_list", stats)

        assert stats["p99_ms"] < 5.0, (
            f"list_patients p99={stats['p99_ms']}ms exceeded 5ms budget"
        )

    def test_search_patients_under_5ms_p99(self):
        repo = InMemoryPatientRepository()
        svc = PatientApplicationService(repo)

        stats = _time_fn(lambda: svc.search_patients("Giulia"), iterations=200)
        _save_result("patient_search_by_name", stats)

        assert stats["p99_ms"] < 5.0

    def test_create_patient_under_10ms_p95(self):
        repo = InMemoryPatientRepository()
        svc = PatientApplicationService(repo)

        def _create():
            req2 = PatientCreateRequest(
                first_name="Bench",
                last_name="User",
                date_of_birth=date(1990, 1, 1),
                email=f"bench_{time.time_ns()}@example.local",
                password_hash="x",
            )
            svc.create_patient(req2)

        stats = _time_fn(_create, iterations=100)
        _save_result("patient_create", stats)

        assert stats["p95_ms"] < 10.0


# ── Consultation service benchmarks ────────────────────────────────────


class TestConsultationServicePerf:
    def test_list_consultations_under_5ms_p99(self):
        repo = InMemoryConsultationRepository()
        svc = ConsultationApplicationService(repo)

        stats = _time_fn(svc.list_consultations, iterations=200)
        _save_result("consultation_list", stats)

        assert stats["p99_ms"] < 5.0

    def test_create_consultation_under_10ms_p95(self):
        repo = InMemoryConsultationRepository()
        svc = ConsultationApplicationService(repo)
        req = ConsultationCreateRequest(patient_id=1)

        stats = _time_fn(
            lambda: svc.create_consultation(req, doctor_id=1), iterations=100
        )
        _save_result("consultation_create", stats)

        assert stats["p95_ms"] < 10.0

    def test_get_consultation_under_2ms_p99(self):
        repo = InMemoryConsultationRepository()
        svc = ConsultationApplicationService(repo)

        stats = _time_fn(lambda: svc.get_consultation(1), iterations=500)
        _save_result("consultation_get_by_id", stats)

        assert stats["p99_ms"] < 2.0


# ── Clinical note generation benchmarks ───────────────────────────────


class TestClinicalNoteGenerationPerf:
    _PROMPT = LlmPromptConfig(
        id="clinical_report_generation_v3",
        prompt_name="Clinical Report Generation",
    )

    def _make_request(self, transcript: str = "Patient reports headache."):
        return ClinicalReportRequest(
            consultation_id=1,
            doctor_id=1,
            patient_id=1,
            transcript_text=transcript,
            normalized_transcript=NormalizedTranscript(
                raw_text=transcript, normalized_text=transcript
            ),
            prompt=self._PROMPT,
        )

    def test_mock_generator_under_20ms_p95(self):
        gen = MockClinicalNoteGenerator()
        req = self._make_request()

        stats = _time_fn(lambda: gen.generate(req), iterations=100)
        _save_result("mock_clinical_note_generation", stats)

        assert stats["p95_ms"] < 20.0

    def test_transcript_normalizer_under_10ms_p95(self):
        from app.domain.clinical_notes.models import TranscriptNormalizationRequest

        normalizer = MockTranscriptNormalizer()
        norm_prompt = LlmPromptConfig(
            id="transcript_normalization_v1",
            prompt_name="Transcript Normalization",
        )

        def _normalise():
            normalizer.normalize(
                TranscriptNormalizationRequest(
                    consultation_id=1,
                    transcript_text="Patient   reports   cough",
                    prompt=norm_prompt,
                )
            )

        stats = _time_fn(_normalise, iterations=200)
        _save_result("transcript_normalizer", stats)

        assert stats["p95_ms"] < 10.0


# ── Document editing benchmarks ────────────────────────────────────────


class TestDocumentEditingPerf:
    def test_single_edit_under_5ms_p95(self):
        def _run():
            gen_repo = InMemoryGeneratedDocumentRepository()
            cons_repo = InMemoryConsultationDocumentRepository()
            svc = DocumentEditingService(gen_repo, cons_repo)
            svc.apply_edits(1, {"diagnosis": "Updated"})

        stats = _time_fn(_run, iterations=100)
        _save_result("document_edit_single_field", stats)

        assert stats["p95_ms"] < 5.0

    def test_version_history_retrieval_under_2ms_p99(self):
        gen_repo = InMemoryGeneratedDocumentRepository()
        cons_repo = InMemoryConsultationDocumentRepository()
        svc = DocumentEditingService(gen_repo, cons_repo)

        # Pre-populate 10 versions
        for i in range(10):
            svc.apply_edits(1, {"diagnosis": f"Version {i}"})

        stats = _time_fn(lambda: svc.get_version_history(1), iterations=500)
        _save_result("version_history_retrieval", stats)

        assert stats["p99_ms"] < 2.0
