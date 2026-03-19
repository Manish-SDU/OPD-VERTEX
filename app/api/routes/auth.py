"""Auth routes for patient, doctor, and admin authentication."""
from datetime import date
from fastapi import APIRouter, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import get_auth_app_service
from app.domain.auth.models import LoginRequest, StaffCreateRequest, User
from app.domain.patients.models import PatientCreateRequest 
from datetime import datetime
from app.core.security import create_access_token

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "auth/register.html", {"page_title": "Register"})

@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request, 
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str = Form(None),
    role: str = Form(...),
    date_of_birth: str = Form(None),
    specialization: str = Form(None),
    license_number: str = Form(None),
) -> HTMLResponse:
    auth_app = get_auth_app_service()
    if date_of_birth:
        dob_date = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
    else:
        dob_date = date(1900, 1, 1)

    try: 
        if role == "patient":
            patient_req = PatientCreateRequest(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password_hash=password, # Sent as plain text to service for hashing
                phone=phone,
                date_of_birth=dob_date,
                role=role
            )
            auth_app.register_patient(patient_req)
        elif role == "doctor":
            staff_req = StaffCreateRequest(
                first_name = first_name,
                last_name=last_name,
                email=email,
                password_hash=password,
                phone=phone,
                role=role, # "doctor" or "admin"
                specialization=specialization,
                license_number=license_number
            )
            auth_app.register_staff(staff_req)

        return RedirectResponse(url="/login?message=Account+created+successfully", status_code=303)
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            {"page_title": "Register", "error": str(e)},
        )


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
    
    token_data = {"sub": user.email, "role": user.role}
    access_token = create_access_token(data=token_data)
    
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True)

    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response 
