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

from pymongo.database import Database

from app.domain.clinical_notes.models import (
    ConsultationDocument,
    ConsultationDocumentRepository,
    GeneratedDocument,
    GeneratedDocumentRepository,
    LlmPromptConfig,
    PromptRepository,
)
from app.domain.email.models import EmailTemplate, EmailTemplateRepository


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

@apply_logging_aspect("repository", "email_templates")
class MongoEmailTemplateRepository(EmailTemplateRepository):
  def __init__(self, db: Database) -> None:
    self.collection = db[names.EMAIL_TEMPLATES]

  def list_templates(self) -> list[EmailTemplate]:
    docs = self.collection.find()
    return [EmailTemplate(id=str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"}) for d in docs]

  def get_by_id(self, template_id: str) -> EmailTemplate | None:
    doc = self.collection.find_one({"_id": ObjectId(template_id)}) if ObjectId.is_valid(template_id) else self.collection.find_one({"_id": template_id})
    if doc:
      return EmailTemplate(id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"})
    return None

@apply_logging_aspect("repository", "prompts")
class MongoPromptRepository(PromptRepository):
  def __init__(self, db: Database) -> None:
    self.collection = db[names.LLM_PROMPTS]

  def list_prompts(self) -> list[LlmPromptConfig]:
    docs = self.collection.find()
    return [LlmPromptConfig(id=str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"}) for d in docs]

  def get_by_id(self, prompt_id: str) -> LlmPromptConfig | None:
    doc = self.collection.find_one({"_id": ObjectId(prompt_id)}) if ObjectId.is_valid(prompt_id) else self.collection.find_one({"_id": prompt_id})
    if doc:
      return LlmPromptConfig(id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"})
    return None


@apply_logging_aspect("repository", "generated_documents")
class MongoGeneratedDocumentRepository(GeneratedDocumentRepository):
  def __init__(self, db: Database) -> None:
    self.collection = db[names.GENERATED_DOCUMENTS]

  def get_by_consultation_id(self, consultation_id: int) -> GeneratedDocument | None:
    doc = self.collection.find_one({"consultation_id": consultation_id})
    if doc:
      return GeneratedDocument(id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"})
    return None

  def save(self, document: GeneratedDocument) -> GeneratedDocument:
    data = document.model_dump(exclude={"id"}, exclude_none=True)
    if document.id:
      # Update existing
      self.collection.replace_one({"_id": ObjectId(document.id)}, data, upsert=True)
      doc_id = document.id
    else:
      result = self.collection.insert_one(data)
      doc_id = str(result.inserted_id)
    doc = self.collection.find_one({"_id": ObjectId(doc_id)})
    return GeneratedDocument(id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"})


@apply_logging_aspect("repository", "consultation_documents")
class MongoConsultationDocumentRepository(ConsultationDocumentRepository):
  def __init__(self, db: Database) -> None:
    self.collection = db[names.CONSULTATION_DOCUMENTS]

  def get_by_consultation_id(self, consultation_id: int) -> ConsultationDocument | None:
    doc = self.collection.find_one({"consultation_id": consultation_id})
    if doc:
      return ConsultationDocument(id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"})
    return None

  def save(self, document: ConsultationDocument) -> ConsultationDocument:
    data = document.model_dump(exclude={"id"}, exclude_none=True)
    if document.id:
      self.collection.replace_one({"_id": ObjectId(document.id)}, data, upsert=True)
      doc_id = document.id
    else:
      result = self.collection.insert_one(data)
      doc_id = str(result.inserted_id)
    doc = self.collection.find_one({"_id": ObjectId(doc_id)})
    return ConsultationDocument(id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"})
