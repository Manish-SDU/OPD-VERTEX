"""Audit application services."""

from __future__ import annotations

from app.domain.audit.models import AuditLog, AuditLogRepository
from app.infrastructure.logging import apply_logging_aspect


@apply_logging_aspect("service", "audit")
class AuditApplicationService:
    def __init__(self, repository: AuditLogRepository) -> None:
        self.repository = repository

    def recent_entries(self) -> list[AuditLog]:
        return self.repository.list_recent()
