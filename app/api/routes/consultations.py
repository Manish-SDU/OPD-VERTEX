"""Consultation routes."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import get_consultation_app_service, get_current_user
from app.domain.consultations.models import ConsultationCreateRequest

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("", response_class=HTMLResponse)
def consultation_list(request: Request, user=Depends(get_current_user)) -> HTMLResponse:
    consultations = get_consultation_app_service().list_consultations()
    return templates.TemplateResponse(
        request,
        "consultations/list.html",
        {"consultations": consultations, "page_title": "Consultations", "user": user},
    )


@router.get("/new", response_class=HTMLResponse)
def consultation_new(request: Request, user=Depends(get_current_user)) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "consultations/create.html", {"page_title": "Start Consultation", "user": user}
    )


@router.post("")
def consultation_create(
    patient_id: int = Form(...), chief_complaint: str = Form(...)
) -> RedirectResponse:
    consultation = get_consultation_app_service().create_consultation(
        ConsultationCreateRequest(patient_id=patient_id),
        doctor_id=1,  # TODO: get from session
    )
    return RedirectResponse(url=f"/consultations/{consultation.id}", status_code=303)


@router.get("/{consultation_id}", response_class=HTMLResponse)
def consultation_detail(consultation_id: int, request: Request, user=Depends(get_current_user)) -> HTMLResponse:
    consultation = get_consultation_app_service().get_consultation(consultation_id)
    return templates.TemplateResponse(
        request,
        "consultations/detail.html",
        {"consultation": consultation, "page_title": "Consultation Detail", "user": user},
    )
