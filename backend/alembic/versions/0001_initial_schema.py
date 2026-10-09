"""initial schema: doctors, patients, appointments

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-06 12:50:56.238353

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "doctors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("specialty", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=180), nullable=False),
        sa.Column(
            "consultation_fee", sa.Numeric(precision=10, scale=2), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=180), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone"),
    )
    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "scheduled",
                "confirmed",
                "completed",
                "cancelled",
                "no_show",
                name="appointment_status",
            ),
            server_default="scheduled",
            nullable=False,
        ),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "duration_minutes > 0", name="ck_appointments_duration_positive"
        ),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_appointments_doctor_id"), "appointments", ["doctor_id"], unique=False
    )
    op.create_index(
        op.f("ix_appointments_patient_id"), "appointments", ["patient_id"], unique=False
    )
    op.create_index(
        op.f("ix_appointments_scheduled_at"),
        "appointments",
        ["scheduled_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_appointments_status"), "appointments", ["status"], unique=False
    )
    op.create_index(
        "ix_appointments_status_scheduled_at",
        "appointments",
        ["status", "scheduled_at"],
        unique=False,
    )
    op.create_index(
        "uq_appointments_doctor_slot",
        "appointments",
        ["doctor_id", "scheduled_at"],
        unique=True,
        postgresql_where=sa.text("status <> 'cancelled'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_appointments_doctor_slot",
        table_name="appointments",
        postgresql_where=sa.text("status <> 'cancelled'"),
    )
    op.drop_index("ix_appointments_status_scheduled_at", table_name="appointments")
    op.drop_index(op.f("ix_appointments_status"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_scheduled_at"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_patient_id"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_doctor_id"), table_name="appointments")
    op.drop_table("appointments")
    op.drop_table("patients")
    op.drop_table("doctors")
    # PostgreSQL keeps enum types outside the table, so drop it explicitly.
    sa.Enum(name="appointment_status").drop(op.get_bind(), checkfirst=True)
