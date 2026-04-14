"""Local LLM health/status routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_llm_health_app_service
from app.application.clinical_notes.services import LlmHealthApplicationService

router = APIRouter()


@router.get("/health")
def llm_health(
    service: LlmHealthApplicationService = Depends(get_llm_health_app_service),
) -> dict:
    status = service.check()
    return status.model_dump()
