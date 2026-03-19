"""Dashboard routes."""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import get_audit_app_service, get_auth_app_service, get_current_user

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def root(request: Request) -> HTMLResponse:
    user = get_auth_app_service().auth_service.get_current_user()
    return templates.TemplateResponse(request, "dashboard/index.html", {"user": user, "page_title": "Home"})


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request, user = Depends(get_current_user)) -> HTMLResponse:
    audit_entries = get_audit_app_service().recent_entries()
    
    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        {"user": user, "audit_entries": audit_entries, "page_title": "Dashboard"},
    )
