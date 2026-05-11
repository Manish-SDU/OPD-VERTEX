"""Consultation routes."""

from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import (
    get_consultation_app_service,
    get_current_user,
    get_patient_app_service,
)
from app.domain.consultations.models import ConsultationCreateRequest

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


def _require_doctor(user=Depends(get_current_user)):
    """Only doctors may start or manage consultations."""
    if user.get("role") != "doctor":
        raise HTTPException(
            status_code=403, detail="Only doctors can manage consultations"
        )
    return user


@router.get("", response_class=HTMLResponse)
def consultation_list(request: Request, user=Depends(get_current_user)) -> HTMLResponse:
    consultations = get_consultation_app_service().list_consultations()
    patients = {p.id: p for p in get_patient_app_service().list_patients()}
    return templates.TemplateResponse(
        request,
        "consultations/list.html",
        {
            "consultations": consultations,
            "patients": patients,
            "page_title": "Consultations",
            "user": user,
        },
    )


@router.get("/new", response_class=HTMLResponse)
def consultation_new(request: Request, user=Depends(_require_doctor)) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "consultations/create.html",
        {"page_title": "Start Consultation", "user": user},
    )


@router.post("")
def consultation_create(
    patient_id: int = Form(...),
    chief_complaint: str = Form(""),
    user=Depends(_require_doctor),
) -> RedirectResponse:
    doctor_id_raw = user.get("sub") or user.get("user_id") or user.get("id")
    if doctor_id_raw is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid session: missing doctor identifier. Please log in again.",
        )

    try:
        doctor_id = int(doctor_id_raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid session: doctor identifier is not numeric. Please log in again.",
        ) from exc

    consultation = get_consultation_app_service().create_consultation(
        ConsultationCreateRequest(
            patient_id=patient_id, chief_complaint=chief_complaint or None
        ),
        doctor_id=doctor_id,
    )
    return RedirectResponse(url=f"/consultations/{consultation.id}", status_code=303)


@router.get("/{consultation_id}", response_class=HTMLResponse)
def consultation_detail(
    consultation_id: int, request: Request, user=Depends(get_current_user)
) -> HTMLResponse:
    consultation = get_consultation_app_service().get_consultation(consultation_id)
    patient = (
        get_patient_app_service().get_patient(consultation.patient_id)
        if consultation
        else None
    )
    return templates.TemplateResponse(
        request,
        "consultations/detail.html",
        {
            "consultation": consultation,
            "patient": patient,
            "page_title": "Consultation Detail",
            "user": user,
        },
    )
