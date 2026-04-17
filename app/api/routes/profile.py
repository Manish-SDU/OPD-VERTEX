from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.api.deps import get_current_user, get_auth_app_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, user=Depends(get_current_user)) -> HTMLResponse:
    subject = user.get("sub")
    role = user.get("role")

    if not subject:
        raise HTTPException(status_code=401, detail="Invalid token")

    auth_service = get_auth_app_service().auth_service
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        user_id = None

    if role == "patient":
        full_user = (
            auth_service.patient_repository.get_by_id(user_id)
            if user_id is not None
            else auth_service.patient_repository.get_by_email(subject)
        )
    elif role == "doctor" or role == "admin":
        full_user = (
            auth_service.staff_repository.get_by_id(user_id)
            if user_id is not None
            else auth_service.staff_repository.get_by_email(subject)
        )
    else:
        raise HTTPException(status_code=401, detail="Unknown role")

    if not full_user:
        raise HTTPException(status_code=404, detail="User not found")

    return templates.TemplateResponse(
        request, "profiles/profile.html", {"user": full_user, "page_title": "Profile"}
    )
