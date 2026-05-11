"""Patient routes."""

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import (
    get_patient_app_service,
    get_current_user,
    get_consultation_app_service,
    get_prescription_app_service,
)

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


def _calculate_age(dob: date | None) -> str:
    if not dob:
        return "N/A"
    today = date.today()
    return str(
        today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    )


@router.get("", response_class=HTMLResponse)
def patient_list(request: Request, user=Depends(get_current_user)) -> HTMLResponse:
    patients = get_patient_app_service().list_patients()
    return templates.TemplateResponse(
        request,
        "patients/list.html",
        {"patients": patients, "page_title": "Patients", "user": user},
    )


@router.get("/search", response_class=JSONResponse)
def patient_search(
    q: str = Query("", min_length=0),
    _user=Depends(get_current_user),
) -> JSONResponse:
    """Return patients matching a name query (for autocomplete)."""
    patients = get_patient_app_service().search_patients(q)
    return JSONResponse(
        [
            {
                "id": p.id,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "email": p.email,
            }
            for p in patients
        ]
    )


@router.get("/{patient_id}", response_class=HTMLResponse)
def patient_detail(
    patient_id: int, request: Request, user=Depends(get_current_user)
) -> HTMLResponse:
    patient = get_patient_app_service().get_patient(patient_id)

    # Fetch consultations and prescriptions for this patient
    all_consultations = get_consultation_app_service().list_consultations()
    all_prescriptions = get_prescription_app_service().list_prescriptions()

    # Filter by patient_id
    consultations = [c for c in all_consultations if c.patient_id == patient_id]
    prescriptions = [p for p in all_prescriptions if p.patient_id == patient_id]

    return templates.TemplateResponse(
        request,
        "patients/detail.html",
        {
            "patient": patient,
            "patient_age": _calculate_age(patient.date_of_birth if patient else None),
            "consultations": consultations,
            "prescriptions": prescriptions,
            "page_title": "Patient Detail",
            "user": user,
        },
    )
