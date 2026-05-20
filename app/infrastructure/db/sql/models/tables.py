"""SQLAlchemy ORM models matching the PDF schema (5 SQL tables).

Mats: implement the real MySQL repositories in
  app/infrastructure/db/sql/repositories/
These ORM models are ready to use with Alembic migrations.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    UniqueConstraint,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ── Table 1: staff ─────────────────────────────────────────────────────


class StaffRow(Base):
    __tablename__ = "staff"

    staff_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    specialization: Mapped[str | None] = mapped_column(String(150), nullable=True)
    license_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True
    )
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    role: Mapped[str] = mapped_column(
        Enum("doctor", "admin", name="staff_role"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        server_onupdate=func.now(),
        onupdate=func.now(),
    )

    consultations = relationship("ConsultationRow", back_populates="doctor")
    prescriptions = relationship("PrescriptionRow", back_populates="doctor")
    appointments = relationship("AppointmentRow", back_populates="doctor")


# ── Table 2: patients ──────────────────────────────────────────────────


class PatientRow(Base):
    __tablename__ = "patients"

    patient_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth = mapped_column(Date, nullable=False)
    gender: Mapped[str | None] = mapped_column(
        Enum("M", "F", "Other", name="patient_gender"), nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    blood_type: Mapped[str | None] = mapped_column(String(5), nullable=True)
    allergies: Mapped[str | None] = mapped_column(Text, nullable=True)
    medical_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    insurance_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(Enum("patient", name="role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        server_onupdate=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (Index("ix_patients_date_of_birth", "date_of_birth"),)

    consultations = relationship("ConsultationRow", back_populates="patient")
    prescriptions = relationship("PrescriptionRow", back_populates="patient")
    appointments = relationship("AppointmentRow", back_populates="patient")


# ── Table 3: consultations ─────────────────────────────────────────────


class ConsultationRow(Base):
    __tablename__ = "consultations"

    consultation_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    doctor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("staff.staff_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.patient_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "recording",
            "transcribing",
            "processing",
            "review",
            "approved",
            "rejected",
            "cancelled",
            name="consultation_status",
        ),
        nullable=False,
        server_default="recording",
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        server_onupdate=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at", name="ck_ended_after_start"
        ),
        CheckConstraint(
            "approved_at IS NULL OR approved_at >= started_at",
            name="ck_approved_after_start",
        ),
        Index("ix_consultations_doctor_id", "doctor_id"),
        Index("ix_consultations_patient_id", "patient_id"),
        Index("ix_consultations_status", "status"),
    )

    doctor = relationship("StaffRow", back_populates="consultations")
    patient = relationship("PatientRow", back_populates="consultations")
    prescriptions = relationship("PrescriptionRow", back_populates="consultation")


# ── Table 4: prescriptions ─────────────────────────────────────────────


class PrescriptionRow(Base):
    __tablename__ = "prescriptions"

    prescription_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    consultation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("consultations.consultation_id"), nullable=False
    )
    doctor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("staff.staff_id"), nullable=False
    )
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.patient_id"), nullable=False
    )
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    medications = mapped_column(JSON, nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_date = mapped_column(Date, nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, server_default="0")
    is_emailed: Mapped[bool] = mapped_column(Boolean, server_default="0")
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        server_onupdate=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_prescriptions_version_positive"),
        UniqueConstraint(
            "consultation_id",
            "version",
            name="uq_prescriptions_consultation_version",
        ),
        Index("ix_prescriptions_consultation_id", "consultation_id"),
        Index("ix_prescriptions_doctor_id", "doctor_id"),
        Index("ix_prescriptions_patient_id", "patient_id"),
    )

    consultation = relationship("ConsultationRow", back_populates="prescriptions")
    doctor = relationship("StaffRow", back_populates="prescriptions")
    patient = relationship("PatientRow", back_populates="prescriptions")


# ── Table 5: audit_logs ────────────────────────────────────────────────


class AuditLogRow(Base):
    __tablename__ = "audit_logs"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_role: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_table: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_timestamp", "timestamp"),
    )


# ── Table 6: appointments ──────────────────────────────────────────────


class AppointmentRow(Base):
    __tablename__ = "appointments"

    appointment_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.patient_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    doctor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("staff.staff_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="30"
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "confirmed",
            "cancelled",
            "completed",
            "no_show",
            name="appointment_status",
        ),
        nullable=False,
        server_default="pending",
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    consultation_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("consultations.consultation_id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        server_onupdate=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_appointments_patient_id", "patient_id"),
        Index("ix_appointments_doctor_id", "doctor_id"),
        Index("ix_appointments_scheduled_at", "scheduled_at"),
        Index("ix_appointments_status", "status"),
    )

    patient = relationship("PatientRow", back_populates="appointments")
    doctor = relationship("StaffRow", back_populates="appointments")
    consultation = relationship("ConsultationRow", foreign_keys=[consultation_id])
