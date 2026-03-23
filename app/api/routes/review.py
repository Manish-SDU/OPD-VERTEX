"""Doctor review workflow routes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import get_review_app_service

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/{consultation_id}", response_class=HTMLResponse)
def review_page(consultation_id: int, request: Request) -> HTMLResponse:
    con_doc, gen_doc, suggestive_review = get_review_app_service().build_review_context(
        consultation_id
    )
    return templates.TemplateResponse(
        request,
        "review/detail.html",
        {
            "consultation_id": consultation_id,
            "consultation_document": con_doc,
            "generated_document": gen_doc,
            "suggestive_review": suggestive_review,
            "page_title": "Review Workflow",
        },
    )


@router.post("/{consultation_id}/approve")
def approve_review(consultation_id: int) -> dict[str, str]:
    return {
        "status": "approved",
        "consultation_id": str(consultation_id),
        "detail": "TODO: persist approval workflow.",
    }


@router.post("/{consultation_id}/reject")
def reject_review(consultation_id: int) -> dict[str, str]:
    return {
        "status": "rejected",
        "consultation_id": str(consultation_id),
        "detail": "TODO: persist rejection workflow.",
    }
