"""Bootstrap synthetic consultation data for local pipeline testing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from logging import getLogger

from pymongo.database import Database
from sqlalchemy.orm import Session

from app.domain.clinical_notes.models import ConsultationDocument, TranscriptDocument
from app.domain.common.types import utcnow
from app.domain.consultations.models import ConsultationStatus
from app.infrastructure.bootstrap.demo_transcripts import DEMO_CONSULTATION_TRANSCRIPTS
from app.infrastructure.db.mongo.repositories.mongo_repos import (
    MongoConsultationDocumentRepository,
)
from app.infrastructure.db.sql.models.tables import (
    ConsultationRow,
    PatientRow,
    StaffRow,
)

logger = getLogger("opd_vertex.infrastructure.bootstrap.mock_consultations")

DEMO_PASSWORD_HASH = "$2b$12$1PEQnpqN.sZC4EWveUcawOg8Cc3tgVRyUVC4huKLUm8pCu2Gw5eY."


@dataclass(frozen=True, slots=True)
class SeededScenario:
    consultation_id: int
    patient_id: int
    started_at: str
    status: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    email: str
    allergies: str
    medical_history: str
    transcript_text: str
    purpose: str


DOCTOR_SEED = {
    "staff_id": 3001,
    "first_name": "Harper",
    "last_name": "Cole",
    "email": "harper.cole@example.local",
    "password_hash": DEMO_PASSWORD_HASH,
    "specialization": "General Medicine",
    "license_number": "DEMO-LIC-3001",
    "phone": "+1-555-0101",
    "role": "doctor",
    "is_active": True,
}


SCENARIOS: tuple[SeededScenario, ...] = (
    SeededScenario(
        consultation_id=4101,
        patient_id=5101,
        started_at="2026-04-10T09:00:00+00:00",
        status=ConsultationStatus.PROCESSING.value,
        first_name="Ava",
        last_name="Miller",
        date_of_birth=date(1988, 5, 11),
        gender="F",
        email="ava.miller@example.local",
        allergies="No known drug allergies",
        medical_history="Mild seasonal allergies",
        purpose="Clean happy-path consultation for full draft generation.",
        transcript_text=DEMO_CONSULTATION_TRANSCRIPTS[4101],
    ),
    SeededScenario(
        consultation_id=4102,
        patient_id=5102,
        started_at="2026-04-10T10:00:00+00:00",
        status=ConsultationStatus.PROCESSING.value,
        first_name="Noah",
        last_name="Perez",
        date_of_birth=date(1979, 2, 7),
        gender="M",
        email="noah.perez@example.local",
        allergies="No known drug allergies",
        medical_history="Hypertension treated with lisinopril",
        purpose="Noisy ASR transcript with recoverable errors for normalization testing.",
        transcript_text=DEMO_CONSULTATION_TRANSCRIPTS[4102],
    ),
    SeededScenario(
        consultation_id=4103,
        patient_id=5103,
        started_at="2026-04-10T11:00:00+00:00",
        status=ConsultationStatus.PROCESSING.value,
        first_name="Mia",
        last_name="Nguyen",
        date_of_birth=date(1995, 9, 3),
        gender="F",
        email="mia.nguyen@example.local",
        allergies="Penicillin allergy causing rash",
        medical_history="Recurrent sinus infections",
        purpose="Medication and allergy conflict case for suggestive review.",
        transcript_text=DEMO_CONSULTATION_TRANSCRIPTS[4103],
    ),
    SeededScenario(
        consultation_id=4104,
        patient_id=5104,
        started_at="2026-04-10T12:00:00+00:00",
        status=ConsultationStatus.PROCESSING.value,
        first_name="Luca",
        last_name="Reed",
        date_of_birth=date(2001, 12, 14),
        gender="Other",
        email="luca.reed@example.local",
        allergies="Not specified",
        medical_history="Not specified",
        purpose="Sparse consultation with many missing fields.",
        transcript_text=DEMO_CONSULTATION_TRANSCRIPTS[4104],
    ),
)


@dataclass(slots=True)
class MockConsultationSeedResult:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0


class MockConsultationBootstrapSeeder:
    def __init__(self, session: Session, mongo_db: Database) -> None:
        self.session = session
        self.mongo_docs = MongoConsultationDocumentRepository(mongo_db)

    def seed(self) -> MockConsultationSeedResult:
        result = MockConsultationSeedResult()
        doctor_action = self._upsert_staff()
        if doctor_action == "inserted":
            result.inserted += 1
        elif doctor_action == "updated":
            result.updated += 1
        else:
            result.skipped += 1
        logger.info("Mock doctor seed %s: %s", doctor_action, DOCTOR_SEED["staff_id"])

        for scenario in SCENARIOS:
            patient_action = self._upsert_patient(scenario)
            consultation_action = self._upsert_consultation(scenario)
            document_action = self._upsert_consultation_document(scenario)

            for action in (patient_action, consultation_action, document_action):
                if action == "inserted":
                    result.inserted += 1
                elif action == "updated":
                    result.updated += 1
                else:
                    result.skipped += 1

            logger.info(
                "Mock consultation seed consultation_id=%s patient=%s patient_action=%s consultation_action=%s mongo_action=%s",
                scenario.consultation_id,
                scenario.patient_id,
                patient_action,
                consultation_action,
                document_action,
            )

        self.session.commit()
        logger.info(
            "Mock consultation bootstrap complete. inserted=%s updated=%s skipped=%s",
            result.inserted,
            result.updated,
            result.skipped,
        )
        return result

    def _upsert_staff(self) -> str:
        existing = self.session.get(StaffRow, DOCTOR_SEED["staff_id"])
        if existing is None:
            self.session.add(StaffRow(**DOCTOR_SEED))
            return "inserted"

        changed = False
        for key, value in DOCTOR_SEED.items():
            if getattr(existing, key) != value:
                setattr(existing, key, value)
                changed = True
        return "updated" if changed else "skipped"

    def _upsert_patient(self, scenario: SeededScenario) -> str:
        payload = {
            "patient_id": scenario.patient_id,
            "first_name": scenario.first_name,
            "last_name": scenario.last_name,
            "date_of_birth": scenario.date_of_birth,
            "gender": scenario.gender,
            "email": scenario.email,
            "phone": "+1-555-0199",
            "address": "Synthetic Demo Address",
            "emergency_contact": "Synthetic Demo Contact",
            "blood_type": None,
            "allergies": scenario.allergies,
            "medical_history": scenario.medical_history,
            "insurance_id": None,
            "password_hash": DEMO_PASSWORD_HASH,
            "role": "patient",
            "is_active": True,
        }
        existing = self.session.get(PatientRow, scenario.patient_id)
        if existing is None:
            self.session.add(PatientRow(**payload))
            return "inserted"

        changed = False
        for key, value in payload.items():
            if getattr(existing, key) != value:
                setattr(existing, key, value)
                changed = True
        return "updated" if changed else "skipped"

    def _upsert_consultation(self, scenario: SeededScenario) -> str:
        payload = {
            "consultation_id": scenario.consultation_id,
            "doctor_id": DOCTOR_SEED["staff_id"],
            "patient_id": scenario.patient_id,
            "status": scenario.status,
            "started_at": datetime_from_iso(scenario.started_at),
            "ended_at": None,
            "approved_at": None,
        }
        existing = self.session.get(ConsultationRow, scenario.consultation_id)
        if existing is None:
            self.session.add(ConsultationRow(**payload))
            return "inserted"

        changed = False
        for key, value in payload.items():
            if getattr(existing, key) != value:
                setattr(existing, key, value)
                changed = True
        return "updated" if changed else "skipped"

    def _upsert_consultation_document(self, scenario: SeededScenario) -> str:
        existing = self.mongo_docs.get_by_consultation_id(scenario.consultation_id)
        document = ConsultationDocument(
            id=existing.id if existing else None,
            consultation_id=scenario.consultation_id,
            transcript=TranscriptDocument(full_text=scenario.transcript_text),
            normalized_transcript=existing.normalized_transcript if existing else None,
            normalization_metadata=existing.normalization_metadata
            if existing
            else None,
            ai_clinical_notes=existing.ai_clinical_notes if existing else None,
            ai_suggestions=existing.ai_suggestions if existing else None,
            doctor_edited_notes=existing.doctor_edited_notes if existing else None,
            edit_history=existing.edit_history if existing else [],
            created_at=existing.created_at if existing else utcnow(),
            updated_at=utcnow(),
        )
        if existing is None:
            self.mongo_docs.save(document)
            return "inserted"

        comparable_existing = existing.model_dump(
            exclude={"id", "created_at", "updated_at"}
        )
        comparable_target = document.model_dump(
            exclude={"id", "created_at", "updated_at"}
        )
        if comparable_existing == comparable_target:
            return "skipped"

        self.mongo_docs.save(document)
        return "updated"


def datetime_from_iso(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value)
