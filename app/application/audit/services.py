"""Audit application services."""

from __future__ import annotations

from typing import Any

from app.domain.audit.models import AuditLog, AuditLogRepository
from app.domain.common.types import utcnow
from app.infrastructure.logging import apply_logging_aspect


@apply_logging_aspect("service", "audit")
class AuditApplicationService:
    def __init__(self, repository: AuditLogRepository) -> None:
        self.repository = repository

    def recent_entries(self) -> list[AuditLog]:
        return self.repository.list_recent()

    def record_entry(
        self,
        *,
        user_id: int,
        user_role: str,
        action: str,
        target_table: str | None = None,
        target_id: int | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        return self.repository.append(
            AuditLog(
                user_id=user_id,
                user_role=user_role,
                action=action,
                target_table=target_table,
                target_id=target_id,
                details=details,
                ip_address=ip_address,
                timestamp=utcnow(),
            )
        )
