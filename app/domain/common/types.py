"""Common domain types."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


def generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
