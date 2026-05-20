"""Doctor review workflow routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.api.deps import (
    get_clinical_notes_app_service,
    get_current_user,
    get_review_app_service,
    get_report_pdf_app_service,
    get_suggestive_review_app_service,
    require_clinical_doctor,
)
from app.application.clinical_notes.services import ClinicalNotesApplicationService
from app.application.pdf.services import ReportPdfApplicationService
from app.application.review.services import ReviewApplicationService
from app.application.suggestive_mode.services import SuggestiveReviewApplicationService

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


class UpdateReportMarkdownRequest(BaseModel):
    report_markdown: str


# =========================
# Report routes first (specific paths before generic /{consultation_id})
# =========================


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
        request=request,
        name="review/report-view.html",
        context={
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
        request=request,
        name="review/report-print.html",
        context={
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
    """Edit and approve the clinical report (doctor only)."""
    require_clinical_doctor(user)

    consultation_document, generated_document, suggestive_review = (
        review_service.build_review_context(consultation_id)
    )
    return templates.TemplateResponse(
        request=request,
        name="review/report-editor.html",
        context={
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
    require_clinical_doctor(user)

    try:
        review_service.update_report_markdown(consultation_id, payload.report_markdown)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "updated",
        "consultation_id": consultation_id,
        "message": "Report markdown updated successfully",
    }


# =========================
# Generic consultation routes after
# =========================


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
        request=request,
        name="review/detail.html",
        context={
            "consultation_id": consultation_id,
            "consultation_document": consultation_document,
            "generated_document": generated_document,
            "suggestive_review": suggestive_review,
            "page_title": "Review Workflow",
            "user": user,
        },
    )


@router.get("/{consultation_id}/pdf")
def download_report_pdf(
    consultation_id: int,
    user=Depends(get_current_user),
    service: ReportPdfApplicationService = Depends(get_report_pdf_app_service),
) -> FileResponse:
    """Download clinical report as PDF via ReportLab."""
    try:
        artifact = service.generate_report_pdf(consultation_id)
        return FileResponse(
            path=artifact.file_path,
            media_type="application/pdf",
            filename=artifact.file_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.post("/{consultation_id}/generate-report")
def generate_report(
    consultation_id: int,
    user=Depends(get_current_user),
    service: ClinicalNotesApplicationService = Depends(get_clinical_notes_app_service),
) -> dict:
    require_clinical_doctor(user)
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
    user=Depends(get_current_user),
    service: ClinicalNotesApplicationService = Depends(get_clinical_notes_app_service),
) -> dict:
    require_clinical_doctor(user)
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
    user=Depends(get_current_user),
    service: SuggestiveReviewApplicationService = Depends(
        get_suggestive_review_app_service
    ),
) -> dict:
    require_clinical_doctor(user)
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
    user=Depends(get_current_user),
    service: SuggestiveReviewApplicationService = Depends(
        get_suggestive_review_app_service
    ),
) -> dict:
    require_clinical_doctor(user)
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
def approve_review(
    consultation_id: int,
    user=Depends(get_current_user),
    service: ReviewApplicationService = Depends(get_review_app_service),
) -> dict:
    require_clinical_doctor(user)
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
    user=Depends(get_current_user),
    service: ReviewApplicationService = Depends(get_review_app_service),
) -> dict:
    require_clinical_doctor(user)
    document = service.reject_review(consultation_id)

    return {
        "status": "rejected",
        "consultation_id": consultation_id,
        "document_status": document.status
        if document
        else "missing_generated_document",
    }


@router.post("/report/{consultation_id}/send-email")
def send_report_email(
    consultation_id: int,
    user=Depends(get_current_user),
    review_service: ReviewApplicationService = Depends(get_review_app_service),
) -> dict:
    """Send approved report to patient email."""
    require_clinical_doctor(user)

    try:
        result = review_service.send_report_to_patient(consultation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to send report email",
        ) from exc

    return {
        "status": "sent",
        "consultation_id": consultation_id,
        "result": result,
    }
