"""Persistence alignment baseline.

Revision ID: 20260325_0001
Revises:
Create Date: 2026-03-25 15:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260325_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "staff",
        sa.Column("staff_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("specialization", sa.String(length=150), nullable=True),
        sa.Column("license_number", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column(
            "role",
            sa.Enum("doctor", "admin", name="staff_role"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("staff_id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("license_number"),
    )

    op.create_table(
        "patients",
        sa.Column("patient_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column(
            "gender",
            sa.Enum("M", "F", "Other", name="patient_gender"),
            nullable=True,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("emergency_contact", sa.String(length=255), nullable=True),
        sa.Column("blood_type", sa.String(length=5), nullable=True),
        sa.Column("allergies", sa.Text(), nullable=True),
        sa.Column("medical_history", sa.Text(), nullable=True),
        sa.Column("insurance_id", sa.String(length=100), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("patient", name="role"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("patient_id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_patients_date_of_birth", "patients", ["date_of_birth"])

    op.create_table(
        "consultations",
        sa.Column("consultation_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "recording",
                "transcribing",
                "processing",
                "review",
                "approved",
                "rejected",
                "cancelled",
                name="consultation_status",
            ),
            server_default="recording",
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="ck_ended_after_start",
        ),
        sa.CheckConstraint(
            "approved_at IS NULL OR approved_at >= started_at",
            name="ck_approved_after_start",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["staff.staff_id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.patient_id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("consultation_id"),
    )
    op.create_index("ix_consultations_doctor_id", "consultations", ["doctor_id"])
    op.create_index("ix_consultations_patient_id", "consultations", ["patient_id"])
    op.create_index("ix_consultations_status", "consultations", ["status"])

    op.create_table(
        "prescriptions",
        sa.Column("prescription_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("consultation_id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("diagnosis", sa.Text(), nullable=False),
        sa.Column("medications", sa.JSON(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        sa.Column("is_approved", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_emailed", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("emailed_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("version >= 1", name="ck_prescriptions_version_positive"),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.consultation_id"]),
        sa.ForeignKeyConstraint(["doctor_id"], ["staff.staff_id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.patient_id"]),
        sa.PrimaryKeyConstraint("prescription_id"),
        sa.UniqueConstraint(
            "consultation_id",
            "version",
            name="uq_prescriptions_consultation_version",
        ),
    )
    op.create_index(
        "ix_prescriptions_consultation_id",
        "prescriptions",
        ["consultation_id"],
    )
    op.create_index("ix_prescriptions_doctor_id", "prescriptions", ["doctor_id"])
    op.create_index("ix_prescriptions_patient_id", "prescriptions", ["patient_id"])

    op.create_table(
        "audit_logs",
        sa.Column("log_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("user_role", sa.String(length=20), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_table", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column(
            "timestamp", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("log_id"),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_timestamp", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_prescriptions_patient_id", table_name="prescriptions")
    op.drop_index("ix_prescriptions_doctor_id", table_name="prescriptions")
    op.drop_index("ix_prescriptions_consultation_id", table_name="prescriptions")
    op.drop_table("prescriptions")

    op.drop_index("ix_consultations_status", table_name="consultations")
    op.drop_index("ix_consultations_patient_id", table_name="consultations")
    op.drop_index("ix_consultations_doctor_id", table_name="consultations")
    op.drop_table("consultations")

    op.drop_index("ix_patients_date_of_birth", table_name="patients")
    op.drop_table("patients")
    op.drop_table("staff")
