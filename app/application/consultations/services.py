"""Consultation application services."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from app.application.consultations.prompts import build_summarizer_messages
from app.application.suggestive_mode.hybrid_suggester import HybridSuggester
from app.application.transcriptions.quality import QualityConfig, annotate
from app.domain.ai.schemas import (
    ConsultationBundle,
    FinalTranscript,
    PatientContext,
    SOAPNote,
    SuggesterOutput,
)
from app.domain.common.types import utcnow
from app.domain.consultations.models import (
    Consultation,
    ConsultationCreateRequest,
    ConsultationRepository,
    ConsultationStatus,
)
from app.infrastructure.logging import apply_logging_aspect

log = logging.getLogger(__name__)

_DEFAULT_RULES_PATH = Path(__file__).parent.parent.parent.parent / "config" / "suggestion_rules.yaml"


@apply_logging_aspect("service", "consultations")
class ConsultationApplicationService:
    def __init__(self, repository: ConsultationRepository) -> None:
        self.repository = repository

    # ------------------------------------------------------------------ #
    # Existing CRUD — unchanged                                           #
    # ------------------------------------------------------------------ #

    def list_consultations(self) -> list[Consultation]:
        return self.repository.list_all()

    def get_consultation(self, consultation_id: int) -> Consultation | None:
        return self.repository.get_by_id(consultation_id)

    def update_status(self, consultation_id: int, status: ConsultationStatus) -> None:
        self.repository.update_status(consultation_id, status)

    def create_consultation(
        self, payload: ConsultationCreateRequest, doctor_id: int
    ) -> Consultation:
        consultation = Consultation(
            doctor_id=doctor_id,
            patient_id=payload.patient_id,
            status=ConsultationStatus.RECORDING,
            started_at=utcnow(),
        )
        return self.repository.create(consultation)

    # ------------------------------------------------------------------ #
    # New AI pipeline lifecycle methods                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def annotate_transcript(
        transcript: FinalTranscript, cfg: QualityConfig | None = None
    ) -> FinalTranscript:
        """Apply hallucination flags and confidence metrics in-place."""
        return annotate(transcript, cfg)

    @staticmethod
    def persist_transcript(
        mongo_db,
        consultation_id: int,
        transcript: FinalTranscript,
        audio_blob_key: str | None = None,
    ) -> str:
        """Upsert the annotated transcript to MongoDB and return the document id."""
        doc = {
            "consultation_id": consultation_id,
            "segments": [s.model_dump() for s in transcript.segments],
            "full_text": transcript.full_text,
            "confidence_avg": transcript.confidence_avg,
            "hallucination_rate": transcript.hallucination_rate,
            "language": transcript.language,
            "duration_s": transcript.duration_s,
            "audio_blob_key": audio_blob_key,
            "created_at": datetime.utcnow(),
        }
        res = mongo_db.transcripts.find_one_and_replace(
            {"consultation_id": consultation_id},
            doc,
            upsert=True,
            return_document=True,
        )
        return str(res["_id"])

    @staticmethod
    async def process(
        mongo_db,
        consultation_id: int,
        patient: PatientContext,
        appointment_at: str,
        llm,
        suggester: HybridSuggester | None = None,
        rules_path: str | Path | None = None,
    ) -> ConsultationBundle:
        """Run summarizer + suggester and persist the results to MongoDB."""
        import asyncio

        transcript_doc = await asyncio.to_thread(
            lambda: mongo_db.transcripts.find_one(
                {"consultation_id": consultation_id},
                sort=[("_id", -1)],
            )
        )
        if transcript_doc is None:
            raise RuntimeError("No transcript persisted for this consultation")

        transcript_text = transcript_doc.get("full_text", "")

        sys_prompt, user_prompt = build_summarizer_messages(
            transcript_text=transcript_text,
            patient=patient,
            appointment_at=appointment_at,
        )
        note: SOAPNote = await llm.generate_json(sys_prompt, user_prompt, SOAPNote, retries=1)

        if suggester is None:
            suggester = HybridSuggester(
                llm=llm,
                rules_path=str(rules_path or _DEFAULT_RULES_PATH),
            )
        suggester_out: SuggesterOutput = await suggester.suggest(transcript_text, note)

        now = datetime.utcnow()
        note_doc = {
            "consultation_id": consultation_id,
            "soap": note.model_dump(mode="json"),
            "generated_at": now,
        }
        presc_doc = {
            "consultation_id": consultation_id,
            "items": [i.model_dump() for i in note.prescription.items],
            "advice": note.prescription.advice,
            "follow_up": note.prescription.follow_up,
            "edited_by_doctor": False,
            "generated_at": now,
        }
        sugg_doc = {
            "consultation_id": consultation_id,
            "items": [s.model_dump() for s in suggester_out.items],
            "generated_at": now,
        }

        await asyncio.to_thread(
            lambda: mongo_db.notes.find_one_and_replace(
                {"consultation_id": consultation_id}, note_doc, upsert=True
            )
        )
        await asyncio.to_thread(
            lambda: mongo_db.prescriptions.find_one_and_replace(
                {"consultation_id": consultation_id}, presc_doc, upsert=True
            )
        )
        await asyncio.to_thread(
            lambda: mongo_db.suggestions.find_one_and_replace(
                {"consultation_id": consultation_id}, sugg_doc, upsert=True
            )
        )

        return ConsultationBundle(
            consultation_id=consultation_id,
            transcript=FinalTranscript(
                full_text=transcript_text,
                confidence_avg=transcript_doc.get("confidence_avg"),
                hallucination_rate=transcript_doc.get("hallucination_rate", 0.0),
            ),
            note=note,
            suggestions=suggester_out,
            generated_at=now,
        )

    @staticmethod
    def reload_bundle(mongo_db, consultation_id: int) -> dict[str, Any]:
        """Read persisted note + prescription + suggestions back from MongoDB."""
        _s = [("_id", -1)]
        transcript = mongo_db.transcripts.find_one(
            {"consultation_id": consultation_id}, sort=_s
        ) or {}
        note = mongo_db.notes.find_one({"consultation_id": consultation_id}, sort=_s)
        presc = mongo_db.prescriptions.find_one(
            {"consultation_id": consultation_id}, sort=_s
        )
        sugg = mongo_db.suggestions.find_one(
            {"consultation_id": consultation_id}, sort=_s
        )
        return {
            "transcript_full_text": transcript.get("full_text", ""),
            "confidence_avg": transcript.get("confidence_avg"),
            "hallucination_rate": transcript.get("hallucination_rate", 0.0),
            "note": (note or {}).get("soap"),
            "prescription": {
                "items": (presc or {}).get("items", []),
                "advice": (presc or {}).get("advice", ""),
                "follow_up": (presc or {}).get("follow_up", ""),
            } if presc else None,
            "suggestions": (sugg or {}).get("items", []),
        }
