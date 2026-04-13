"""Prescription routes."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import get_prescription_app_service, get_current_user

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("", response_class=HTMLResponse)
def prescription_list(request: Request, user=Depends(get_current_user)) -> HTMLResponse:
    prescriptions = get_prescription_app_service().list_prescriptions()
    return templates.TemplateResponse(
        request,
        "prescriptions/list.html",
        {"prescriptions": prescriptions, "page_title": "Prescriptions", "user": user},
    )
