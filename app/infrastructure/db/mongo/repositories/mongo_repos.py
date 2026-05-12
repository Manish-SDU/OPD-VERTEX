"""MongoDB repository stubs.

Mats and Gabriele: implement each class below. They receive a pymongo Database
and must translate between domain models (app/domain/*/models.py)
and raw MongoDB documents.

Collections to implement (see names.py for collection name constants):
  1. email_templates   -> EmailTemplateRepository
  2. llm_prompts       -> PromptRepository
  3. generated_documents -> GeneratedDocumentRepository
  4. consultation_documents -> ConsultationDocumentRepository

See TODO.md for step-by-step instructions.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database

from app.domain.clinical_notes.models import (
    ConsultationDocument,
    ConsultationDocumentRepository,
    GeneratedDocument,
    GeneratedDocumentRepository,
    LlmPromptConfig,
    PrescriptionArtifact,
    PrescriptionArtifactRepository,
    PromptRepository,
)
from app.domain.email.models import EmailTemplate, EmailTemplateRepository
from app.domain.transcriptions.models import (
    TemporaryTranscriptChunk,
    TemporaryTranscriptChunkRepository,
)


# ── Example pattern (repeat for each repository) ───────────────────────
#
#   class MongoEmailTemplateRepository(EmailTemplateRepository):
#       def __init__(self, db: Database) -> None:
#           self.collection = db["email_templates"]
#
#       def list_templates(self) -> list[EmailTemplate]:
#           docs = self.collection.find()
#           return [EmailTemplate(id=str(d["_id"]), ...) for d in docs]
#
# Each method should:
#   1. Query/insert/update via pymongo collection methods
#   2. Convert the raw dict to/from the domain Pydantic model
#   3. Return the domain model

# ── Real MongoDB repository implementations ─────────────────────────────
from app.infrastructure.db.mongo.collections import names
from bson import ObjectId
from app.infrastructure.logging import apply_logging_aspect

TemporaryTranscriptChunk.model_rebuild()


def _document_filter(document_id: str) -> dict:
    if ObjectId.is_valid(document_id):
        return {"_id": ObjectId(document_id)}
    return {"_id": document_id}


@apply_logging_aspect("repository", "email_templates")
class MongoEmailTemplateRepository(EmailTemplateRepository):
    def __init__(self, db: Database) -> None:
        self.collection = db[names.EMAIL_TEMPLATES]

    def list_templates(self) -> list[EmailTemplate]:
        docs = self.collection.find()
        return [
            EmailTemplate(
                id=str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"}
            )
            for d in docs
        ]

    def get_by_id(self, template_id: str) -> EmailTemplate | None:
        doc = self.collection.find_one(_document_filter(template_id))
        if doc:
            return EmailTemplate(
                id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"}
            )
        return None

    def save(self, template: EmailTemplate) -> EmailTemplate:
        now = datetime.now(UTC)
        existing = self.collection.find_one(_document_filter(template.id))
        data = template.model_dump(exclude={"id"}, exclude_none=True)
        data["created_at"] = existing.get("created_at", now) if existing else now
        data["updated_at"] = now

        self.collection.replace_one(_document_filter(template.id), data, upsert=True)
        saved = self.collection.find_one(_document_filter(template.id))
        return EmailTemplate(
            id=str(saved["_id"]), **{k: v for k, v in saved.items() if k != "_id"}
        )


@apply_logging_aspect("repository", "prompts")
class MongoPromptRepository(PromptRepository):
    def __init__(self, db: Database) -> None:
        self.collection = db[names.LLM_PROMPTS]

    def list_prompts(self) -> list[LlmPromptConfig]:
        docs = self.collection.find()
        return [
            LlmPromptConfig(
                id=str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"}
            )
            for d in docs
        ]

    def get_by_id(self, prompt_id: str) -> LlmPromptConfig | None:
        doc = self.collection.find_one(_document_filter(prompt_id))
        if doc:
            return LlmPromptConfig(
                id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"}
            )
        return None

    def save(self, prompt: LlmPromptConfig) -> LlmPromptConfig:
        now = datetime.now(UTC)
        existing = self.collection.find_one(_document_filter(prompt.id))
        data = prompt.model_dump(exclude={"id"}, exclude_none=True)
        data["created_at"] = existing.get("created_at", now) if existing else now
        data["updated_at"] = now

        self.collection.replace_one(_document_filter(prompt.id), data, upsert=True)
        saved = self.collection.find_one(_document_filter(prompt.id))
        return LlmPromptConfig(
            id=str(saved["_id"]), **{k: v for k, v in saved.items() if k != "_id"}
        )


@apply_logging_aspect("repository", "generated_documents")
class MongoGeneratedDocumentRepository(GeneratedDocumentRepository):
    def __init__(self, db: Database) -> None:
        self.collection = db[names.GENERATED_DOCUMENTS]
        self.collection.create_index(
            [("consultation_id", ASCENDING)],
            unique=True,
            name="uq_generated_documents_consultation_id",
        )

    def get_by_consultation_id(self, consultation_id: int) -> GeneratedDocument | None:
        doc = self.collection.find_one({"consultation_id": consultation_id})
        if doc:
            return GeneratedDocument(
                id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"}
            )
        return None

    def save(self, document: GeneratedDocument) -> GeneratedDocument:
        data = document.model_dump(exclude={"id"}, exclude_none=True)
        if document.id:
            # Update existing
            self.collection.replace_one(
                {"_id": ObjectId(document.id)}, data, upsert=True
            )
            doc_id = document.id
        else:
            result = self.collection.insert_one(data)
            doc_id = str(result.inserted_id)
        doc = self.collection.find_one({"_id": ObjectId(doc_id)})
        return GeneratedDocument(
            id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"}
        )


@apply_logging_aspect("repository", "consultation_documents")
class MongoConsultationDocumentRepository(ConsultationDocumentRepository):
    def __init__(self, db: Database) -> None:
        self.collection = db[names.CONSULTATION_DOCUMENTS]
        self.collection.create_index(
            [("consultation_id", ASCENDING)],
            unique=True,
            name="uq_consultation_documents_consultation_id",
        )

    def get_by_consultation_id(
        self, consultation_id: int
    ) -> ConsultationDocument | None:
        doc = self.collection.find_one({"consultation_id": consultation_id})
        if doc:
            return ConsultationDocument(
                id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"}
            )
        return None

    def save(self, document: ConsultationDocument) -> ConsultationDocument:
        data = document.model_dump(exclude={"id"}, exclude_none=True)
        if document.id:
            self.collection.replace_one(
                {"_id": ObjectId(document.id)}, data, upsert=True
            )
            doc_id = document.id
        else:
            result = self.collection.insert_one(data)
            doc_id = str(result.inserted_id)
        doc = self.collection.find_one({"_id": ObjectId(doc_id)})
        return ConsultationDocument(
            id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"}
        )


@apply_logging_aspect("repository", "prescription_artifacts")
class MongoPrescriptionArtifactRepository(PrescriptionArtifactRepository):
    def __init__(self, db: Database) -> None:
        self.collection = db[names.PRESCRIPTION_ARTIFACTS]
        self.collection.create_index(
            [("prescription_id", ASCENDING), ("version", DESCENDING)],
            name="ix_prescription_artifacts_prescription_version",
        )
        self.collection.create_index(
            [("consultation_id", ASCENDING)],
            name="ix_prescription_artifacts_consultation_id",
        )

    def get_latest_by_prescription_id(
        self, prescription_id: int
    ) -> PrescriptionArtifact | None:
        doc = self.collection.find_one(
            {"prescription_id": prescription_id},
            sort=[("version", DESCENDING)],
        )
        if doc:
            return PrescriptionArtifact(
                id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"}
            )
        return None

    def save(self, artifact: PrescriptionArtifact) -> PrescriptionArtifact:
        now = datetime.now(UTC)
        data = artifact.model_dump(exclude={"id"}, exclude_none=True)
        data["updated_at"] = now
        if "created_at" not in data:
            data["created_at"] = now

        if artifact.id:
            self.collection.replace_one(
                {"_id": ObjectId(artifact.id)},
                data,
                upsert=True,
            )
            doc_id = artifact.id
        else:
            result = self.collection.insert_one(data)
            doc_id = str(result.inserted_id)

        doc = self.collection.find_one({"_id": ObjectId(doc_id)})
        return PrescriptionArtifact(
            id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"}
        )


@apply_logging_aspect("repository", "temporary_transcript_chunks")
class MongoTemporaryTranscriptChunkRepository(TemporaryTranscriptChunkRepository):
    def __init__(self, db):
        self.collection = db["temporary_transcript_chunks"]

    def save_chunk(self, chunk: TemporaryTranscriptChunk) -> TemporaryTranscriptChunk:
        """Save incoming chunk immediately."""
        doc = chunk.model_dump(exclude={"id"})
        result = self.collection.insert_one(doc)
        chunk.id = str(result.inserted_id)
        return chunk

    def get_chunks_by_consultation(
        self, consultation_id: int
    ) -> list[TemporaryTranscriptChunk]:
        """Fetch all partial chunks when save button is pressed."""
        chunks = self.collection.find(
            {"consultation_id": consultation_id}, sort=[("chunk_id", 1)]
        )
        return [TemporaryTranscriptChunk(**doc) for doc in chunks]

    def delete_chunks_by_consultation(self, consultation_id: int) -> None:
        """Clean up after successful save."""
        self.collection.delete_many({"consultation_id": consultation_id})

    def delete_chunks_by_session(self, session_id: str):
        """Delete all chunks for a specific session."""
        self.collection.delete_many({"session_id": session_id})
