"""Auth placeholder routes."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import get_auth_app_service
from app.domain.auth.models import LoginRequest

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "auth/login.html", {"page_title": "Login"})


@router.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)) -> HTMLResponse:
    staff = get_auth_app_service().login(LoginRequest(username=username, password=password))
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        {"page_title": "Login", "staff": staff, "message": "Mock login executed."},
    )


@router.get("/logout")
def logout() -> dict[str, str]:
    return {"message": "Mock logout placeholder."}
