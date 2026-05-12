"""Admin configuration routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import (
    email_template_repository,
    get_audit_app_service,
    get_current_user,
    prompt_repository,
)
from app.domain.common.types import utcnow

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()

_STATUS_MESSAGES = {
    "prompt_saved": "Prompt saved and audit entry recorded.",
    "template_saved": "Email template saved and audit entry recorded.",
}


def _require_admin(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admins can manage settings")
    return user


def _user_id(user: dict) -> int:
    try:
        return int(user.get("sub") or 0)
    except (TypeError, ValueError):
        return 0


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _csv_values(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _admin_redirect(status: str) -> RedirectResponse:
    return RedirectResponse(url=f"/admin/config?status={status}", status_code=303)


def _template_context(request: Request, user: dict, status: str | None = None) -> dict:
    return {
        "request": request,
        "prompts": prompt_repository().list_prompts(),
        "email_templates": email_template_repository().list_templates(),
        "audit_entries": get_audit_app_service().recent_entries(),
        "status_message": _STATUS_MESSAGES.get(status or ""),
        "page_title": "Admin Configuration",
        "user": user,
    }


@router.get("/config", response_class=HTMLResponse)
def admin_config(
    request: Request,
    status: str | None = None,
    user=Depends(_require_admin),
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "admin/config.html",
        _template_context(request, user, status),
    )


@router.post("/prompts/{prompt_id}")
def update_prompt_config(
    prompt_id: str,
    request: Request,
    prompt_name: str = Form(...),
    model_target: str = Form(...),
    temperature: float = Form(...),
    max_tokens: int = Form(...),
    system_prompt: str = Form(...),
    user_prompt_template: str = Form(...),
    user=Depends(_require_admin),
) -> RedirectResponse:
    repo = prompt_repository()
    existing = repo.get_by_id(prompt_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Prompt config not found")

    saved = repo.save(
        existing.model_copy(
            update={
                "prompt_name": prompt_name.strip(),
                "model_target": model_target.strip(),
                "temperature": temperature,
                "max_tokens": max_tokens,
                "system_prompt": system_prompt.strip(),
                "user_prompt_template": user_prompt_template.strip(),
                "version": existing.version + 1,
                "updated_at": utcnow(),
            }
        )
    )
    get_audit_app_service().record_entry(
        user_id=_user_id(user),
        user_role=user.get("role", "admin"),
        action="ADMIN_PROMPT_UPDATED",
        target_table="llm_prompts",
        details={"prompt_id": saved.id, "prompt_name": saved.prompt_name},
        ip_address=_client_ip(request),
    )
    return _admin_redirect("prompt_saved")


@router.post("/email-templates/{template_id}")
def update_email_template(
    template_id: str,
    request: Request,
    template_name: str = Form(...),
    subject_template: str = Form(...),
    body_template: str = Form(...),
    placeholders: str = Form(""),
    from_email: str = Form(""),
    reply_to: str = Form(""),
    user=Depends(_require_admin),
) -> RedirectResponse:
    repo = email_template_repository()
    existing = repo.get_by_id(template_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Email template not found")

    saved = repo.save(
        existing.model_copy(
            update={
                "template_name": template_name.strip(),
                "subject_template": subject_template.strip(),
                "body_template": body_template.strip(),
                "placeholders": _csv_values(placeholders),
                "from_email": from_email.strip(),
                "reply_to": reply_to.strip(),
                "version": existing.version + 1,
                "updated_at": utcnow(),
            }
        )
    )
    get_audit_app_service().record_entry(
        user_id=_user_id(user),
        user_role=user.get("role", "admin"),
        action="ADMIN_EMAIL_TEMPLATE_UPDATED",
        target_table="email_templates",
        details={"template_id": saved.id, "template_name": saved.template_name},
        ip_address=_client_ip(request),
    )
    return _admin_redirect("template_saved")
