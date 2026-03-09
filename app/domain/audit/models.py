"""Audit models and contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class AuditLog(BaseModel):
    id: str
    actor_id: str
    action: str
    entity_type: str
    entity_id: str
    metadata: dict[str, str] = Field(default_factory=dict)


class AuditLogRepository(ABC):
    @abstractmethod
    def list_recent(self) -> list[AuditLog]:
        """Return recent audit logs."""

    @abstractmethod
    def append(self, entry: AuditLog) -> AuditLog:
        """Persist audit entry."""
