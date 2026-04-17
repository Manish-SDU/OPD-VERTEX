"""Dashboard routes."""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import (
    get_audit_app_service,
    get_current_user,
    get_optional_current_user,
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

    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        {"user": user, "audit_entries": audit_entries, "page_title": "Dashboard"},
    )
