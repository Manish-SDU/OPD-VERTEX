"""Doctor review workflow routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.api.deps import (
    get_clinical_notes_app_service,
    get_current_user,
    get_review_app_service,
    get_suggestive_review_app_service,
)
from app.application.clinical_notes.services import ClinicalNotesApplicationService
from app.application.review.services import ReviewApplicationService
from app.application.suggestive_mode.services import SuggestiveReviewApplicationService

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


class UpdateReportMarkdownRequest(BaseModel):
    report_markdown: str


@router.get("/{consultation_id}", response_class=HTMLResponse)
def review_page(
    consultation_id: int,
    request: Request,
    user=Depends(get_current_user),
    review_service: ReviewApplicationService = Depends(get_review_app_service),
) -> HTMLResponse:
    consultation_document, generated_document, suggestive_review = (
        review_service.build_review_context(consultation_id)
    )
    return templates.TemplateResponse(
        request,
        "review/detail.html",
        {
            "consultation_id": consultation_id,
            "consultation_document": consultation_document,
            "generated_document": generated_document,
            "suggestive_review": suggestive_review,
            "page_title": "Review Workflow",
            "user": user,
        },
    )


@router.post("/{consultation_id}/generate-report")
def generate_report(
    consultation_id: int,
    service: ClinicalNotesApplicationService = Depends(get_clinical_notes_app_service),
) -> dict:
    try:
        document = service.generate_report(consultation_id, regenerate=False)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": "generated",
        "consultation_id": consultation_id,
        "document_status": document.status,
        "report": document.generated_output.model_dump(),
        "report_markdown": document.generated_output.report_markdown,
    }


@router.post("/{consultation_id}/regenerate")
def regenerate_report(
    consultation_id: int,
    service: ClinicalNotesApplicationService = Depends(get_clinical_notes_app_service),
) -> dict:
    try:
        document = service.generate_report(consultation_id, regenerate=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": "regenerated",
        "consultation_id": consultation_id,
        "document_status": document.status,
        "report": document.generated_output.model_dump(),
        "report_markdown": document.generated_output.report_markdown,
    }


@router.post("/{consultation_id}/suggestive-review")
def run_suggestive_review(
    consultation_id: int,
    service: SuggestiveReviewApplicationService = Depends(
        get_suggestive_review_app_service
    ),
) -> dict:
    try:
        review = service.run_review(consultation_id, regenerate=False)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": "reviewed",
        "consultation_id": consultation_id,
        "suggestive_review": review.model_dump(),
    }


@router.post("/{consultation_id}/approve")
def approve_review(
    consultation_id: int,
    service: ReviewApplicationService = Depends(get_review_app_service),
) -> dict:
    try:
        prescription = service.approve_review(consultation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": "approved",
        "consultation_id": consultation_id,
        "prescription_id": prescription.id,
        "version": prescription.version,
    }


@router.post("/{consultation_id}/reject")
def reject_review(
    consultation_id: int,
    service: ReviewApplicationService = Depends(get_review_app_service),
) -> dict:
    document = service.reject_review(consultation_id)
    return {
        "status": "rejected",
        "consultation_id": consultation_id,
        "document_status": document.status
        if document
        else "missing_generated_document",
    }


@router.get("/report/{consultation_id}", response_class=HTMLResponse)
def view_report(
    consultation_id: int,
    request: Request,
    user=Depends(get_current_user),
    review_service: ReviewApplicationService = Depends(get_review_app_service),
) -> HTMLResponse:
    """Display the clinical report in read-only mode."""
    consultation_document, generated_document, suggestive_review = (
        review_service.build_review_context(consultation_id)
    )
    return templates.TemplateResponse(
        request,
        "review/report-view.html",
        {
            "consultation_id": consultation_id,
            "consultation_document": consultation_document,
            "generated_document": generated_document,
            "suggestive_review": suggestive_review,
            "page_title": "View Clinical Report",
            "user": user,
        },
    )


@router.get("/report/{consultation_id}/print", response_class=HTMLResponse)
def print_report(
    consultation_id: int,
    request: Request,
    user=Depends(get_current_user),
    review_service: ReviewApplicationService = Depends(get_review_app_service),
) -> HTMLResponse:
    """Display a clean print/export view for browser PDF saving."""
    consultation_document, generated_document, suggestive_review = (
        review_service.build_review_context(consultation_id)
    )
    return templates.TemplateResponse(
        request,
        "review/report-print.html",
        {
            "consultation_id": consultation_id,
            "consultation_document": consultation_document,
            "generated_document": generated_document,
            "suggestive_review": suggestive_review,
            "page_title": "Print Clinical Report",
            "user": user,
        },
    )


@router.get("/report/{consultation_id}/edit", response_class=HTMLResponse)
def edit_report(
    consultation_id: int,
    request: Request,
    user=Depends(get_current_user),
    review_service: ReviewApplicationService = Depends(get_review_app_service),
) -> HTMLResponse:
    """Edit and approve the clinical report (doctor/admin only)."""
    if user.get("role") not in ("doctor", "admin"):
        raise HTTPException(
            status_code=403, detail="Only doctors and admins can edit reports"
        )

    consultation_document, generated_document, suggestive_review = (
        review_service.build_review_context(consultation_id)
    )
    return templates.TemplateResponse(
        request,
        "review/report-editor.html",
        {
            "consultation_id": consultation_id,
            "consultation_document": consultation_document,
            "generated_document": generated_document,
            "suggestive_review": suggestive_review,
            "page_title": "Edit & Approve Clinical Report",
            "user": user,
        },
    )


@router.post("/report/{consultation_id}/update-markdown")
def update_report_markdown(
    consultation_id: int,
    payload: UpdateReportMarkdownRequest,
    user=Depends(get_current_user),
    review_service: ReviewApplicationService = Depends(get_review_app_service),
) -> dict:
    """Update the markdown content of the clinical report."""
    if user.get("role") not in ("doctor", "admin"):
        raise HTTPException(
            status_code=403, detail="Only doctors and admins can edit reports"
        )

    try:
        review_service.update_report_markdown(consultation_id, payload.report_markdown)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "updated",
        "consultation_id": consultation_id,
        "message": "Report markdown updated successfully",
    }
