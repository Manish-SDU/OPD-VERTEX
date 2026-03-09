"""Security placeholders for future auth hardening."""

from __future__ import annotations

from typing import Any


def create_session_payload(user_id: str, role: str) -> dict[str, Any]:
    """Return minimal mock session data until real auth is implemented."""
    return {"user_id": user_id, "role": role}
