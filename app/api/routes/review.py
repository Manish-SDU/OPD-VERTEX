"""Doctor review workflow routes."""

from __future__ import annotations

import logging

import markdown as md
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.api.deps import (
    generated_repository,
    get_clinical_notes_app_service,
    get_current_user,
    get_review_app_service,
    get_smtp_email_service,
    get_suggestive_review_app_service,
    patient_repository,
)
from app.application.clinical_notes.services import ClinicalNotesApplicationService
from app.application.review.services import ReviewApplicationService
from app.application.suggestive_mode.services import SuggestiveReviewApplicationService
from app.domain.ai.schemas import Attachment

log = logging.getLogger(__name__)

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


@router.post("/{consultation_id}/suggestive-review/regenerate")
def regenerate_suggestive_review(
    consultation_id: int,
    service: SuggestiveReviewApplicationService = Depends(
        get_suggestive_review_app_service
    ),
) -> dict:
    try:
        review = service.run_review(consultation_id, regenerate=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": "regenerated",
        "consultation_id": consultation_id,
        "suggestive_review": review.model_dump(),
    }


@router.get("/{consultation_id}/suggestive-review")
def get_suggestive_review(
    consultation_id: int,
    service: SuggestiveReviewApplicationService = Depends(
        get_suggestive_review_app_service
    ),
) -> dict:
    try:
        review = service.get_review(consultation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "status": "loaded",
        "consultation_id": consultation_id,
        "suggestive_review": review.model_dump(),
    }


@router.post("/{consultation_id}/approve")
async def approve_review(
    consultation_id: int,
    service: ReviewApplicationService = Depends(get_review_app_service),
) -> dict:
    try:
        prescription = service.approve_review(consultation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Email the report PDF (HTML) to the patient
    try:
        gen_doc = generated_repository().get_by_consultation_id(consultation_id)
        patient = patient_repository().get_by_id(prescription.patient_id)
        if gen_doc and patient and patient.email:
            markdown_text = gen_doc.generated_output.report_markdown or ""
            report_html = md.markdown(markdown_text, extensions=["tables", "fenced_code"])
            full_html = (
                "<!DOCTYPE html><html><head>"
                "<meta charset='UTF-8'>"
                "<style>"
                "body{font-family:Georgia,serif;max-width:800px;margin:2rem auto;padding:0 1.5rem;color:#1a1a2e;}"
                "h1,h2,h3{font-family:'Segoe UI',sans-serif;}"
                "table{border-collapse:collapse;width:100%;}"
                "th,td{border:1px solid #ccc;padding:0.5rem 0.75rem;text-align:left;}"
                "th{background:#f0f4ff;}"
                "hr{border:none;border-top:1px solid #d6deea;margin:1.5rem 0;}"
                "pre,code{background:#f5f5f5;padding:0.25rem 0.5rem;border-radius:4px;font-size:0.9em;}"
                "</style>"
                "</head><body>"
                f"{report_html}"
                "</body></html>"
            )
            await get_smtp_email_service().send(
                to=patient.email,
                subject=f"Your Clinical Report – Consultation #{consultation_id}",
                body_html=full_html,
                body_text=markdown_text,
                attachments=[
                    Attachment(
                        filename=f"clinical_report_{consultation_id}.html",
                        content=full_html.encode("utf-8"),
                        content_type="text/html",
                    )
                ],
            )
            log.info(
                "Report emailed to patient=%s for consultation=%s",
                patient.email,
                consultation_id,
            )
    except Exception as exc:
        log.warning("Failed to email report for consultation=%s: %s", consultation_id, exc)

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
