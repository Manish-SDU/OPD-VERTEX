"""Dashboard routes."""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import (
    get_appointment_app_service,
    get_audit_app_service,
    get_consultation_app_service,
    get_current_user,
    get_optional_current_user,
    get_patient_app_service,
    get_prescription_app_service,
)

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def root(request: Request) -> HTMLResponse:
    if not get_optional_current_user(request):
        return RedirectResponse(url="/login", status_code=303)
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request, user=Depends(get_current_user)) -> HTMLResponse:
    audit_entries = get_audit_app_service().recent_entries()
    role = user.get("role")
    user_id = int(user.get("sub", 0))

    stats: dict = {}
    if role == "doctor":
        all_consultations = get_consultation_app_service().list_consultations()
        all_prescriptions = get_prescription_app_service().list_prescriptions()
        pending = [
            c
            for c in all_consultations
            if getattr(c, "status", None) == "pending_review"
        ]
        stats = {
            "patient_count": len(get_patient_app_service().list_patients()),
            "consultation_count": len(all_consultations),
            "prescription_count": len(all_prescriptions),
            "pending_reviews": len(pending),
        }
    elif role == "patient":
        all_consultations = get_consultation_app_service().list_consultations()
        all_prescriptions = get_prescription_app_service().list_prescriptions()
        my_consultations = [c for c in all_consultations if c.patient_id == user_id]
        my_prescriptions = [p for p in all_prescriptions if p.patient_id == user_id]
        upcoming_appointments = get_appointment_app_service().list_upcoming(
            current_user=user
        )
        stats = {
            "appointment_count": len(upcoming_appointments),
            "prescription_count": len(my_prescriptions),
            "record_count": len(my_consultations),
        }

    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        {
            "user": user,
            "audit_entries": audit_entries,
            "page_title": "Dashboard",
            **stats,
        },
    )
