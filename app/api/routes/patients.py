"""Patient routes."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import get_patient_app_service
from app.domain.patients.models import PatientCreateRequest

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("", response_class=HTMLResponse)
def patient_list(request: Request) -> HTMLResponse:
    patients = get_patient_app_service().list_patients()
    return templates.TemplateResponse(request, "patients/list.html", {"patients": patients, "page_title": "Patients"})


@router.get("/new", response_class=HTMLResponse)
def patient_new(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "patients/create.html", {"page_title": "New Patient"})


@router.post("")
def patient_create(first_name: str = Form(...), last_name: str = Form(...), email: str | None = Form(default=None)) -> RedirectResponse:
    get_patient_app_service().create_patient(PatientCreateRequest(first_name=first_name, last_name=last_name, email=email))
    return RedirectResponse(url="/patients", status_code=303)


@router.get("/{patient_id}", response_class=HTMLResponse)
def patient_detail(patient_id: str, request: Request) -> HTMLResponse:
    patient = get_patient_app_service().get_patient(patient_id)
    return templates.TemplateResponse(request, "patients/detail.html", {"patient": patient, "page_title": "Patient Detail"})
