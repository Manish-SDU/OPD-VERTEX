"""Admin configuration routes."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import email_template_repository, get_current_user, prompt_repository

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/config", response_class=HTMLResponse)
def admin_config(request: Request, user=Depends(get_current_user)) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "admin/config.html",
        {
            "prompts": prompt_repository().list_prompts(),
            "email_templates": email_template_repository().list_templates(),
            "page_title": "Admin Configuration",
            "user": user,
        },
    )
