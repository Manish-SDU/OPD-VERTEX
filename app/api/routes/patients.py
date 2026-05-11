"""Patient routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

log = logging.getLogger(__name__)

from app.api.deps import (
    get_consultation_app_service,
    get_current_user,
    get_patient_app_service,
    get_prescription_app_service,
    get_smtp_email_service,
)

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


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

    all_consultations = get_consultation_app_service().list_consultations()
    all_prescriptions = get_prescription_app_service().list_prescriptions()

    consultations = [c for c in all_consultations if c.patient_id == patient_id]
    prescriptions = [p for p in all_prescriptions if p.patient_id == patient_id]

    return templates.TemplateResponse(
        request,
        "patients/detail.html",
        {
            "patient": patient,
            "consultations": consultations,
            "prescriptions": prescriptions,
            "page_title": "Patient Detail",
            "user": user,
        },
    )


@router.post("/{patient_id}/send-invitation")
async def send_patient_invitation(
    patient_id: int,
    request: Request,
    user=Depends(get_current_user),
) -> JSONResponse:
    """Generate a single-use login link and email it to the patient."""
    svc = get_patient_app_service()
    patient = svc.get_patient(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    doctor_id = int(user["sub"])
    raw_token = svc.generate_invitation_token(patient_id=patient_id, invited_by=doctor_id)

    base_url = str(request.base_url).rstrip("/")
    link = f"{base_url}/patient-link/{raw_token}"

    body_html = (
        f"<p>Dear {patient.first_name},</p>"
        f"<p>Your doctor has shared your consultation records with you.</p>"
        f"<p><a href='{link}'>Click here to access your records</a></p>"
        f"<p>This link expires in 72 hours and can only be used once.</p>"
    )
    body_text = (
        f"Dear {patient.first_name},\n\n"
        f"Your doctor has shared your consultation records with you.\n\n"
        f"Access your records here: {link}\n\n"
        f"This link expires in 72 hours and can only be used once."
    )

    email_sent = False
    try:
        mailer = get_smtp_email_service()
        await mailer.send(
            to=patient.email,
            subject="Your secure login link — OPD-Vertex",
            body_html=body_html,
            body_text=body_text,
        )
        email_sent = True
    except Exception as exc:
        log.warning("Failed to email invitation link to %s: %s", patient.email, exc)

    return JSONResponse({
        "status": "sent" if email_sent else "link_only",
        "email": patient.email,
        "link": link,
    })
