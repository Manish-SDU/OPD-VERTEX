"""MongoDB repository stubs.

Gabriele: implement each class below. They receive a pymongo Database
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
