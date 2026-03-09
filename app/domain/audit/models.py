"""Audit models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditLog(BaseModel):
    """Maps to SQL table: audit_logs."""

    id: int | None = None
    user_id: int
    user_role: str
    action: str
    target_table: str | None = None
    target_id: int | None = None
    details: dict[str, Any] | None = Field(default=None)
    ip_address: str | None = None
    timestamp: datetime | None = None


class AuditLogRepository(ABC):
    @abstractmethod
    def list_recent(self) -> list[AuditLog]:
        """Return recent audit logs."""

    @abstractmethod
    def append(self, entry: AuditLog) -> AuditLog:
        """Persist audit entry."""
