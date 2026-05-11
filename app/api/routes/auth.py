"""Auth routes for authentication."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import get_auth_app_service, get_optional_current_user, get_patient_app_service
from app.domain.auth.models import LoginRequest
from app.core.security import create_access_token

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    if get_optional_current_user(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(
        request, "auth/login.html", {"page_title": "Login"}
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request, email: str = Form(...), password: str = Form(...)
) -> HTMLResponse:
    """Unified login - tries staff first, then patient."""
    auth_app = get_auth_app_service()
    user = auth_app.login(LoginRequest(email=email, password=password))
    if not user:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"page_title": "Login", "error": "Invalid credentials"},
            status_code=401,
        )

    token_data = {"sub": str(user.id), "role": user.role}
    access_token = create_access_token(data=token_data)

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True)

    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response


@router.get("/patient-link/{token}", response_class=HTMLResponse)
def patient_link_login(token: str, request: Request) -> HTMLResponse:
    """Single-use login endpoint for patients arriving via a doctor-generated link."""
    patient = get_patient_app_service().consume_invitation_token(token)
    if patient is None:
        return templates.TemplateResponse(
            request,
            "auth/patient_link_invalid.html",
            {"page_title": "Link Invalid"},
            status_code=410,
        )
    token_data = {"sub": str(patient.id), "role": "patient"}
    access_token = create_access_token(data=token_data)
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response
