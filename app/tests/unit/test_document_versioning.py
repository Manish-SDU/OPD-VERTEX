"""Unit tests for document versioning and editing service."""

from __future__ import annotations

import pytest

from app.application.clinical_notes.editing import DocumentEditingService
from app.domain.clinical_notes.models import (
    GeneratedDocumentStatus,
)
from app.infrastructure.persistence.in_memory.repositories import (
    InMemoryConsultationDocumentRepository,
    InMemoryGeneratedDocumentRepository,
)


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def gen_repo():
    return InMemoryGeneratedDocumentRepository()


@pytest.fixture
def cons_doc_repo():
    return InMemoryConsultationDocumentRepository()


@pytest.fixture
def editing_service(gen_repo, cons_doc_repo):
    return DocumentEditingService(gen_repo, cons_doc_repo)


# ── Apply edits ────────────────────────────────────────────────────────


class TestApplyEdits:
    def test_single_field_edit_changes_value(self, editing_service, gen_repo):
        doc = editing_service.apply_edits(1, {"diagnosis": "Updated diagnosis"})
        assert doc.generated_output.diagnosis == "Updated diagnosis"

    def test_edit_bumps_version_counter(self, editing_service):
        doc = editing_service.apply_edits(1, {"diagnosis": "v2 diagnosis"})
        assert doc.version == 2

    def test_multiple_edits_in_one_call(self, editing_service):
        doc = editing_service.apply_edits(
            1,
            {
                "diagnosis": "Hypertension stage 2",
                "chief_complaint": "High blood pressure",
            },
        )
        assert doc.generated_output.diagnosis == "Hypertension stage 2"
        assert doc.generated_output.chief_complaint == "High blood pressure"

    def test_edit_records_doctor_edit_entries(self, editing_service):
        doc = editing_service.apply_edits(
            1, {"diagnosis": "New diagnosis"}, edit_summary="Doctor correction"
        )
        assert any(e.field_path == "diagnosis" for e in doc.doctor_edits)

    def test_edit_stores_old_value_in_doctor_edits(self, editing_service, gen_repo):
        original = gen_repo.get_by_consultation_id(1)
        original_diagnosis = original.generated_output.diagnosis

        doc = editing_service.apply_edits(1, {"diagnosis": "Changed"})

        edit = next(e for e in doc.doctor_edits if e.field_path == "diagnosis")
        assert edit.old_value == original_diagnosis
        assert edit.new_value == "Changed"

    def test_edit_sets_status_to_revised(self, editing_service):
        doc = editing_service.apply_edits(1, {"follow_up": "2 weeks"})
        assert doc.status == GeneratedDocumentStatus.REVISED

    def test_edit_stores_snapshot_in_version_history(self, editing_service, gen_repo):
        original_diagnosis = gen_repo.get_by_consultation_id(
            1
        ).generated_output.diagnosis
        doc = editing_service.apply_edits(1, {"diagnosis": "Post-edit"})

        assert len(doc.version_history) == 1
        assert doc.version_history[0].version == 1
        assert doc.version_history[0].snapshot.diagnosis == original_diagnosis

    def test_sequential_edits_accumulate_history(self, editing_service):
        editing_service.apply_edits(1, {"diagnosis": "Edit 1"})
        doc = editing_service.apply_edits(1, {"diagnosis": "Edit 2"})

        assert doc.version == 3
        assert len(doc.version_history) == 2

    def test_raises_when_document_not_found(self, editing_service):
        with pytest.raises(ValueError, match="No generated document found"):
            editing_service.apply_edits(9999, {"diagnosis": "Irrelevant"})


# ── Version history ────────────────────────────────────────────────────


class TestGetVersionHistory:
    def test_empty_history_on_fresh_document(self, editing_service):
        history = editing_service.get_version_history(1)
        assert history == []

    def test_history_grows_with_each_edit(self, editing_service):
        editing_service.apply_edits(1, {"diagnosis": "First edit"})
        editing_service.apply_edits(1, {"diagnosis": "Second edit"})

        history = editing_service.get_version_history(1)
        assert len(history) == 2

    def test_history_for_missing_document_returns_empty(self, editing_service):
        assert editing_service.get_version_history(9999) == []


# ── Restore version ────────────────────────────────────────────────────


class TestRestoreVersion:
    def test_restore_reverts_to_snapshot_content(self, editing_service, gen_repo):
        original_diagnosis = gen_repo.get_by_consultation_id(
            1
        ).generated_output.diagnosis
        editing_service.apply_edits(1, {"diagnosis": "Changed diagnosis"})

        doc = editing_service.restore_version(1, target_version=1)

        assert doc.generated_output.diagnosis == original_diagnosis

    def test_restore_bumps_version(self, editing_service):
        editing_service.apply_edits(1, {"diagnosis": "Changed"})
        doc = editing_service.restore_version(1, target_version=1)
        assert doc.version == 3  # v1 → edit → v2 → restore → v3

    def test_restore_preserves_current_in_history(self, editing_service):
        editing_service.apply_edits(1, {"diagnosis": "Changed"})
        doc = editing_service.restore_version(1, target_version=1)

        # The v2 state must be stored in history before we overwrote it
        v2_entry = next((e for e in doc.version_history if e.version == 2), None)
        assert v2_entry is not None
        assert v2_entry.snapshot.diagnosis == "Changed"

    def test_restore_raises_for_missing_version(self, editing_service):
        editing_service.apply_edits(1, {"diagnosis": "Changed"})
        with pytest.raises(ValueError, match="Version 99 not found"):
            editing_service.restore_version(1, target_version=99)


# ── Diff versions ──────────────────────────────────────────────────────


class TestDiffVersions:
    def test_diff_between_version_and_current_shows_changed_fields(
        self, editing_service
    ):
        editing_service.apply_edits(
            1,
            {"diagnosis": "Updated diagnosis", "follow_up": "1 week"},
        )
        diffs = editing_service.diff_versions(1, version_a=1, version_b=0)

        assert "diagnosis" in diffs
        assert diffs["diagnosis"]["b"] == "Updated diagnosis"

    def test_diff_with_no_changes_returns_empty(self, editing_service):
        # Apply the same value twice so that v2 snapshot == current state
        editing_service.apply_edits(1, {"diagnosis": "Same"})
        editing_service.apply_edits(1, {"diagnosis": "Same"})
        # version_history[1] holds v2 snapshot (diagnosis="Same")
        # current doc also has diagnosis="Same"
        # diff between v2 snapshot and live doc (0) should have no diagnosis change
        diffs = editing_service.diff_versions(1, version_a=2, version_b=0)
        assert "diagnosis" not in diffs

    def test_diff_raises_for_missing_version(self, editing_service):
        with pytest.raises(ValueError, match="Version 55 not found"):
            editing_service.diff_versions(1, version_a=55, version_b=0)
