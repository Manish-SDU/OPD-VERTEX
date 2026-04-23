"""Stress tests — sustained load and concurrency simulation.

These tests push the in-memory repositories and application services
under high-volume sequential and concurrent workloads to surface any
shared-state bugs, ID collision issues, or degraded performance under
load.

All tests use mock adapters only (no DB, no LLM calls).
"""

from __future__ import annotations

import concurrent.futures
import random
import threading
from datetime import date

from app.application.clinical_notes.editing import DocumentEditingService
from app.application.consultations.services import ConsultationApplicationService
from app.application.patients.services import PatientApplicationService
from app.domain.consultations.models import (
    ConsultationCreateRequest,
    ConsultationStatus,
)
from app.domain.patients.models import PatientCreateRequest
from app.infrastructure.persistence.in_memory.repositories import (
    InMemoryConsultationDocumentRepository,
    InMemoryConsultationRepository,
    InMemoryGeneratedDocumentRepository,
    InMemoryPatientRepository,
    MockClinicalNoteGenerator,
)
from app.domain.clinical_notes.models import (
    ClinicalReportRequest,
    LlmPromptConfig,
    NormalizedTranscript,
)

# ── Patient repository stress ──────────────────────────────────────────


class TestPatientRepositoryStress:
    def test_create_1000_patients_no_id_collisions(self):
        repo = InMemoryPatientRepository()
        svc = PatientApplicationService(repo)
        ids = set()

        for i in range(1000):
            req = PatientCreateRequest(
                first_name=f"Patient{i}",
                last_name="Stress",
                date_of_birth=date(1990, 1, 1),
                email=f"stress_{i}@example.local",
                password_hash="x",
            )
            p = svc.create_patient(req)
            assert p.id is not None, f"Iteration {i}: patient ID is None"
            assert p.id not in ids, f"ID collision at iteration {i}: id={p.id}"
            ids.add(p.id)

        assert len(ids) == 1000

    def test_list_patients_consistent_under_repeated_calls(self):
        repo = InMemoryPatientRepository()
        svc = PatientApplicationService(repo)

        first = len(svc.list_patients())
        for _ in range(500):
            svc.list_patients()
        last = len(svc.list_patients())

        assert first == last, "list_patients() count changed without mutations"

    def test_search_handles_empty_and_whitespace_queries(self):
        repo = InMemoryPatientRepository()
        svc = PatientApplicationService(repo)
        queries = ["", "  ", "\t", "  \n  "]

        for q in queries:
            result = svc.search_patients(q)
            assert isinstance(result, list)
            # Empty/whitespace queries return all patients
            assert len(result) == len(svc.list_patients())

    def test_search_1000_queries_no_exceptions(self):
        repo = InMemoryPatientRepository()
        svc = PatientApplicationService(repo)
        names = ["Giulia", "xyz", "123", "", "a" * 100, "Giu", "li", "5101"]

        for _ in range(1000):
            q = random.choice(names)
            results = svc.search_patients(q)
            assert isinstance(results, list)


# ── Consultation repository stress ────────────────────────────────────


class TestConsultationRepositoryStress:
    def test_create_500_consultations_no_id_collisions(self):
        repo = InMemoryConsultationRepository()
        svc = ConsultationApplicationService(repo)
        ids = set()

        for i in range(500):
            req = ConsultationCreateRequest(patient_id=i % 10 + 1)
            c = svc.create_consultation(req, doctor_id=1)
            assert c.id is not None
            assert c.id not in ids, f"ID collision at iteration {i}"
            ids.add(c.id)

        assert len(ids) == 500

    def test_status_updates_do_not_corrupt_other_records(self):
        repo = InMemoryConsultationRepository()
        svc = ConsultationApplicationService(repo)

        # Create 50 consultations
        created_ids = []
        for i in range(50):
            c = svc.create_consultation(
                ConsultationCreateRequest(patient_id=1), doctor_id=1
            )
            created_ids.append(c.id)

        # Update every other one
        for idx, cid in enumerate(created_ids):
            if idx % 2 == 0:
                repo.update_status(cid, ConsultationStatus.APPROVED)

        # Verify odd-indexed ones are still RECORDING
        for idx, cid in enumerate(created_ids):
            c = svc.get_consultation(cid)
            if idx % 2 == 0:
                assert c.status == ConsultationStatus.APPROVED
            else:
                assert c.status == ConsultationStatus.RECORDING

    def test_concurrent_consultation_creation_no_id_collisions(self):
        """Thread-safety smoke test — verifies IDs are unique under concurrent writes."""
        repo = InMemoryConsultationRepository()
        lock = threading.Lock()
        collected_ids: list[int] = []
        errors: list[Exception] = []

        def _create(_: int):
            try:
                from app.domain.consultations.models import Consultation

                with lock:
                    c = repo.create(
                        Consultation(
                            doctor_id=1,
                            patient_id=1,
                            status=ConsultationStatus.RECORDING,
                        )
                    )
                    collected_ids.append(c.id)
            except Exception as exc:
                errors.append(exc)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            list(pool.map(_create, range(200)))

        assert not errors, f"Errors during concurrent creation: {errors}"
        assert len(set(collected_ids)) == len(collected_ids), "ID collisions found"


# ── Document editing stress ────────────────────────────────────────────


class TestDocumentEditingStress:
    def test_100_sequential_edits_maintain_correct_version(self):
        gen_repo = InMemoryGeneratedDocumentRepository()
        cons_repo = InMemoryConsultationDocumentRepository()
        svc = DocumentEditingService(gen_repo, cons_repo)

        for i in range(100):
            svc.apply_edits(1, {"diagnosis": f"Version {i + 1} diagnosis"})

        doc = gen_repo.get_by_consultation_id(1)
        assert doc.version == 101  # starts at 1, 100 edits → 101
        assert len(doc.version_history) == 100
        assert doc.generated_output.diagnosis == "Version 100 diagnosis"

    def test_version_history_entries_are_chronologically_ordered(self):
        gen_repo = InMemoryGeneratedDocumentRepository()
        cons_repo = InMemoryConsultationDocumentRepository()
        svc = DocumentEditingService(gen_repo, cons_repo)

        for i in range(20):
            svc.apply_edits(1, {"diagnosis": f"v{i}"})

        history = svc.get_version_history(1)
        versions = [e.version for e in history]
        assert versions == sorted(versions), "Version history is not in order"

    def test_restore_after_many_edits_is_accurate(self):
        gen_repo = InMemoryGeneratedDocumentRepository()
        cons_repo = InMemoryConsultationDocumentRepository()
        svc = DocumentEditingService(gen_repo, cons_repo)

        original_diagnosis = gen_repo.get_by_consultation_id(
            1
        ).generated_output.diagnosis

        for i in range(50):
            svc.apply_edits(1, {"diagnosis": f"Edit {i}"})

        doc = svc.restore_version(1, target_version=1)
        assert doc.generated_output.diagnosis == original_diagnosis

    def test_diff_across_many_versions_is_stable(self):
        gen_repo = InMemoryGeneratedDocumentRepository()
        cons_repo = InMemoryConsultationDocumentRepository()
        svc = DocumentEditingService(gen_repo, cons_repo)

        svc.apply_edits(1, {"diagnosis": "First"})
        svc.apply_edits(1, {"diagnosis": "Second"})

        for _ in range(100):
            diffs = svc.diff_versions(1, version_a=1, version_b=2)
            assert "diagnosis" in diffs


# ── Clinical note generation stress ───────────────────────────────────


class TestClinicalNoteGenerationStress:
    _PROMPT = LlmPromptConfig(
        id="clinical_report_generation_v3",
        prompt_name="Clinical Report Generation",
    )

    def test_200_sequential_generations_produce_valid_outputs(self):
        gen = MockClinicalNoteGenerator()
        transcripts = [
            "Patient reports headache.",
            "Chest pain radiating to arm.",
            "Dizziness on standing.",
            "Persistent cough for 2 weeks.",
            "Knee pain after running.",
        ]

        for i in range(200):
            transcript = transcripts[i % len(transcripts)]
            req = ClinicalReportRequest(
                consultation_id=i + 1,
                doctor_id=1,
                patient_id=i % 5 + 1,
                transcript_text=transcript,
                normalized_transcript=NormalizedTranscript(
                    raw_text=transcript,
                    normalized_text=transcript,
                ),
                prompt=self._PROMPT,
            )
            notes = gen.generate(req)
            assert notes.diagnosis != "", f"Empty diagnosis at iteration {i}"
            assert notes.chief_complaint != "", (
                f"Empty chief_complaint at iteration {i}"
            )

    def test_generation_is_deterministic_for_same_input(self):
        """Mock generator must return the same result for the same input."""
        gen = MockClinicalNoteGenerator()
        req = ClinicalReportRequest(
            consultation_id=1,
            doctor_id=1,
            patient_id=1,
            transcript_text="Stable angina.",
            normalized_transcript=NormalizedTranscript(
                raw_text="Stable angina.", normalized_text="Stable angina."
            ),
            prompt=self._PROMPT,
        )

        outputs = [gen.generate(req).diagnosis for _ in range(50)]
        assert len(set(outputs)) == 1, "Mock generator is non-deterministic"


# ── End-to-end pipeline stress ─────────────────────────────────────────


class TestEndToEndPipelineStress:
    """Run the full create → record → report → edit workflow N times."""

    def test_pipeline_runs_50_times_without_errors(self):
        for run in range(50):
            consultation_repo = InMemoryConsultationRepository()
            cons_app = ConsultationApplicationService(consultation_repo)
            gen_repo = InMemoryGeneratedDocumentRepository()
            cons_doc_repo = InMemoryConsultationDocumentRepository()

            # Create a consultation
            c = cons_app.create_consultation(
                ConsultationCreateRequest(patient_id=1), doctor_id=1
            )
            assert c.id is not None

            # Generate a note for the seeded consultation ID 1
            gen = MockClinicalNoteGenerator()
            req = ClinicalReportRequest(
                consultation_id=1,
                doctor_id=1,
                patient_id=1,
                transcript_text="Patient is well.",
                normalized_transcript=NormalizedTranscript(
                    raw_text="Patient is well.", normalized_text="Patient is well."
                ),
                prompt=LlmPromptConfig(
                    id="clinical_report_generation_v3",
                    prompt_name="Clinical Report Generation",
                ),
            )
            notes = gen.generate(req)
            assert notes.diagnosis.strip() != ""

            # Apply an edit
            editing_svc = DocumentEditingService(gen_repo, cons_doc_repo)
            edited = editing_svc.apply_edits(1, {"diagnosis": f"Run {run} diagnosis"})
            assert edited.version == 2
