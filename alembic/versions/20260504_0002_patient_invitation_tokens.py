"""Add patient_invitation_tokens table.

Revision ID: 20260504_0002
Revises: 20260325_0001
Create Date: 2026-05-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260504_0002"
down_revision = "20260325_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_invitation_tokens",
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("invited_by", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.patient_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["invited_by"], ["staff.staff_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("token"),
    )
    op.create_index(
        "ix_pit_patient_id", "patient_invitation_tokens", ["patient_id"]
    )
    op.create_index(
        "ix_pit_expires_at", "patient_invitation_tokens", ["expires_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_pit_expires_at", table_name="patient_invitation_tokens")
    op.drop_index("ix_pit_patient_id", table_name="patient_invitation_tokens")
    op.drop_table("patient_invitation_tokens")
