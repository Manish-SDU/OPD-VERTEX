"""Document editing & versioning application service.

Allows doctors to apply field-level edits to a generated document,
automatically snapshotting the previous state as an immutable version
entry so the full audit trail is preserved.
"""

from __future__ import annotations

from typing import Any

from app.domain.clinical_notes.models import (
    ConsultationDocumentRepository,
    DoctorEdit,
    DocumentVersionEntry,
    GeneratedDocument,
    GeneratedDocumentRepository,
    GeneratedDocumentStatus,
)
from app.domain.common.types import utcnow
from app.infrastructure.logging import apply_logging_aspect


@apply_logging_aspect("service", "document_editing")
class DocumentEditingService:
    """Manages doctor edits and version snapshots on generated documents."""

    def __init__(
        self,
        generated_doc_repo: GeneratedDocumentRepository,
        consultation_doc_repo: ConsultationDocumentRepository,
    ) -> None:
        self._gen_repo = generated_doc_repo
        self._cons_repo = consultation_doc_repo

    # ── Public API ──────────────────────────────────────────────────────

    def apply_edits(
        self,
        consultation_id: int,
        edits: dict[str, Any],
        edit_summary: str = "",
    ) -> GeneratedDocument:
        """Apply a dict of ``{field_path: new_value}`` edits to the generated
        document, bump the version counter, and persist a snapshot of the
        previous state into ``version_history``."""
        doc = self._load_or_raise(consultation_id)

        # Snapshot the pre-edit state
        snapshot = doc.generated_output.model_copy(deep=True)
        recorded_edits: list[DoctorEdit] = []

        for field_path, new_value in edits.items():
            old_value = self._get_field(doc.generated_output, field_path)
            self._set_field(doc.generated_output, field_path, new_value)
            recorded_edits.append(
                DoctorEdit(
                    field_path=field_path,
                    old_value=str(old_value),
                    new_value=str(new_value),
                    edited_at=utcnow(),
                )
            )

        doc.version_history.append(
            DocumentVersionEntry(
                version=doc.version,
                snapshot=snapshot,
                edit_summary=edit_summary or f"Edited: {', '.join(edits.keys())}",
                created_at=utcnow(),
            )
        )
        doc.doctor_edits.extend(recorded_edits)
        doc.version += 1
        doc.status = GeneratedDocumentStatus.REVISED
        doc.updated_at = utcnow()

        return self._gen_repo.save(doc)

    def get_version_history(self, consultation_id: int) -> list[DocumentVersionEntry]:
        """Return the full version history list for a consultation."""
        return self._gen_repo.get_version_history(consultation_id)

    def restore_version(
        self, consultation_id: int, target_version: int
    ) -> GeneratedDocument:
        """Restore a previous version snapshot as the current document.

        The current state is automatically saved as a new snapshot before
        the restore so no data is ever lost.
        """
        doc = self._load_or_raise(consultation_id)

        entry = next(
            (e for e in doc.version_history if e.version == target_version), None
        )
        if entry is None:
            raise ValueError(
                f"Version {target_version} not found in history for "
                f"consultation {consultation_id}."
            )

        # Preserve current state before overwriting
        doc.version_history.append(
            DocumentVersionEntry(
                version=doc.version,
                snapshot=doc.generated_output.model_copy(deep=True),
                edit_summary=f"Auto-snapshot before restoring to v{target_version}",
                created_at=utcnow(),
            )
        )

        doc.generated_output = entry.snapshot.model_copy(deep=True)
        doc.version += 1
        doc.status = GeneratedDocumentStatus.REVISED
        doc.updated_at = utcnow()

        return self._gen_repo.save(doc)

    def diff_versions(
        self, consultation_id: int, version_a: int, version_b: int
    ) -> dict[str, dict[str, str]]:
        """Return a field-level diff between two stored versions.

        Returns ``{field_path: {"a": old_value, "b": new_value}}`` for every
        top-level field that changed.  If ``version_a`` or ``version_b`` is
        ``None``/``0`` it falls back to the current live document.
        """
        doc = self._load_or_raise(consultation_id)

        def _get_snapshot(v: int) -> dict:
            if v == 0 or v is None:
                return doc.generated_output.model_dump()
            entry = next((e for e in doc.version_history if e.version == v), None)
            if entry is None:
                raise ValueError(
                    f"Version {v} not found for consultation {consultation_id}."
                )
            return entry.snapshot.model_dump()

        snap_a = _get_snapshot(version_a)
        snap_b = _get_snapshot(version_b)

        diffs: dict[str, dict[str, str]] = {}
        all_keys = set(snap_a) | set(snap_b)
        for key in all_keys:
            va = str(snap_a.get(key, ""))
            vb = str(snap_b.get(key, ""))
            if va != vb:
                diffs[key] = {"a": va, "b": vb}
        return diffs

    # ── Private helpers ─────────────────────────────────────────────────

    def _load_or_raise(self, consultation_id: int) -> GeneratedDocument:
        doc = self._gen_repo.get_by_consultation_id(consultation_id)
        if doc is None:
            raise ValueError(
                f"No generated document found for consultation {consultation_id}."
            )
        return doc

    @staticmethod
    def _get_field(notes_obj: Any, field_path: str) -> Any:
        obj = notes_obj
        for part in field_path.split("."):
            obj = getattr(obj, part, None)
            if obj is None:
                return ""
        return obj

    @staticmethod
    def _set_field(notes_obj: Any, field_path: str, value: Any) -> None:
        parts = field_path.split(".")
        obj = notes_obj
        for part in parts[:-1]:
            obj = getattr(obj, part)
        setattr(obj, parts[-1], value)
