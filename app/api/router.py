"""Main API router registration."""

from fastapi import APIRouter

from app.api.routes import (
    admin,
    appointments,
    auth,
    consultations,
    dashboard,
    health,
    llm,
    patients,
    prescriptions,
    review,
    transcriptions,
    profile,
)

router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(auth.router, tags=["auth"])
router.include_router(dashboard.router, tags=["dashboard"])
router.include_router(llm.router, prefix="/llm", tags=["llm"])
router.include_router(patients.router, prefix="/patients", tags=["patients"])
router.include_router(
    consultations.router, prefix="/consultations", tags=["consultations"]
)
router.include_router(review.router, prefix="/review", tags=["review"])
router.include_router(
    prescriptions.router, prefix="/prescriptions", tags=["prescriptions"]
)
router.include_router(admin.router, prefix="/admin", tags=["admin"])

router.include_router(
    transcriptions.router, prefix="/transcriptions", tags=["transcriptions"]
)
router.include_router(
    appointments.router, prefix="/appointments", tags=["appointments"]
)
router.include_router(profile.router, tags=["profile"])
