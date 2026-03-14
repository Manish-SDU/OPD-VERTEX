"""Auth routes for patient, doctor, and admin authentication."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import get_auth_app_service
from app.domain.auth.models import LoginRequest, User

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "auth/login.html", {"page_title": "Login"})


@router.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, email: str = Form(...), password: str = Form(...)) -> HTMLResponse:
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

    # TODO: redirect based on user.role / user.user_type when dashboards exist
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        {"page_title": "Login", "user": user, "message": "Login succeeded."},
    )


@router.get("/logout")
def logout() -> dict[str, str]:
    return {"message": "Mock logout placeholder."}
