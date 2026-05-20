"""Appointment routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import (
    get_appointment_app_service,
    get_current_user,
    get_patient_app_service,
    get_consultation_app_service,
    require_clinical_doctor,
    require_doctor_or_admin,
    staff_repository,
)
from app.core.exceptions import AppError
from app.domain.appointments.models import AppointmentCreateRequest

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


# ── List ───────────────────────────────────────────────────────────────


@router.get("", response_class=HTMLResponse)
def appointment_list(request: Request, user=Depends(get_current_user)) -> HTMLResponse:
    svc = get_appointment_app_service()
    appointments = svc.list_appointments(current_user=user)

    # Build patient/doctor name lookup maps for the template
    all_patients = {p.id: p for p in get_patient_app_service().list_patients()}

    return templates.TemplateResponse(
        request,
        "appointments/list.html",
        {
            "appointments": appointments,
            "patients": all_patients,
            "user": user,
            "page_title": "Appointments",
        },
    )


# ── New form ────────────────────────────────────────────────────────────


@router.get("/new", response_class=HTMLResponse)
def appointment_new_form(
    request: Request, user=Depends(get_current_user)
) -> HTMLResponse:
    all_patients = get_patient_app_service().list_patients()
    all_doctors = [s for s in staff_repository().list_all() if s.role == "doctor"]
    return templates.TemplateResponse(
        request,
        "appointments/new.html",
        {
            "patients": all_patients,
            "doctors": all_doctors,
            "user": user,
            "page_title": "Book Appointment",
        },
    )


# ── Create ──────────────────────────────────────────────────────────────


@router.post("")
def appointment_create(
    request: Request,
    patient_id: int = Form(...),
    doctor_id: int = Form(...),
    scheduled_at: str = Form(...),
    duration_minutes: int = Form(30),
    reason: str = Form(...),
    notes: str = Form(""),
    user=Depends(get_current_user),
):
    try:
        scheduled_dt = datetime.fromisoformat(scheduled_at)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid scheduled_at format")

    # Patients can only book for themselves
    role = user.get("role")
    user_id = int(user.get("sub", 0))
    if role == "patient":
        patient_id = user_id

    req = AppointmentCreateRequest(
        patient_id=patient_id,
        doctor_id=doctor_id,
        scheduled_at=scheduled_dt,
        duration_minutes=duration_minutes,
        reason=reason,
        notes=notes or None,
    )
    try:
        appointment = get_appointment_app_service().create_appointment(req)
    except AppError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return RedirectResponse(url=f"/appointments/{appointment.id}", status_code=303)


# ── Detail ──────────────────────────────────────────────────────────────


@router.get("/{appointment_id}", response_class=HTMLResponse)
def appointment_detail(
    appointment_id: int, request: Request, user=Depends(get_current_user)
) -> HTMLResponse:
    svc = get_appointment_app_service()
    appointment = svc.get_appointment(appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")

    all_patients = {p.id: p for p in get_patient_app_service().list_patients()}
    consultation = None
    if appointment.consultation_id:
        consultation = get_consultation_app_service().get_consultation(
            appointment.consultation_id
        )

    return templates.TemplateResponse(
        request,
        "appointments/detail.html",
        {
            "appointment": appointment,
            "patients": all_patients,
            "consultation": consultation,
            "user": user,
            "page_title": f"Appointment #{appointment_id}",
        },
    )


# ── Confirm ─────────────────────────────────────────────────────────────


@router.post("/{appointment_id}/confirm")
def appointment_confirm(
    appointment_id: int,
    request: Request,
    user=Depends(get_current_user),
):
    require_doctor_or_admin(user)
    try:
        get_appointment_app_service().confirm_appointment(appointment_id)
    except AppError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return RedirectResponse(url=f"/appointments/{appointment_id}", status_code=303)


# ── Cancel ──────────────────────────────────────────────────────────────


@router.post("/{appointment_id}/cancel")
def appointment_cancel(
    appointment_id: int,
    request: Request,
    user=Depends(get_current_user),
):
    try:
        get_appointment_app_service().cancel_appointment(appointment_id)
    except AppError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return RedirectResponse(url=f"/appointments/{appointment_id}", status_code=303)


# ── No-show ─────────────────────────────────────────────────────────────


@router.post("/{appointment_id}/no-show")
def appointment_no_show(
    appointment_id: int,
    request: Request,
    user=Depends(get_current_user),
):
    require_doctor_or_admin(user)
    try:
        get_appointment_app_service().mark_no_show(appointment_id)
    except AppError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return RedirectResponse(url=f"/appointments/{appointment_id}", status_code=303)


# ── Start consultation ──────────────────────────────────────────────────


@router.post("/{appointment_id}/start-consultation")
def appointment_start_consultation(
    appointment_id: int,
    request: Request,
    user=Depends(get_current_user),
):
    require_clinical_doctor(user)
    try:
        _appointment, consultation = (
            get_appointment_app_service().start_consultation_from_appointment(
                appointment_id, current_user=user
            )
        )
    except AppError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return RedirectResponse(url=f"/consultations/{consultation.id}", status_code=303)
