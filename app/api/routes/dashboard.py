"""Dashboard routes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import get_audit_app_service, get_auth_app_service

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def root(request: Request) -> HTMLResponse:
    staff = get_auth_app_service().auth_service.get_current_staff()
    return templates.TemplateResponse(request, "dashboard/index.html", {"staff": staff, "page_title": "Home"})


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request) -> HTMLResponse:
    staff = get_auth_app_service().auth_service.get_current_staff()
    audit_entries = get_audit_app_service().recent_entries()
    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        {"staff": staff, "audit_entries": audit_entries, "page_title": "Dashboard"},
    )
