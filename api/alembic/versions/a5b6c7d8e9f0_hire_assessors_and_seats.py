"""Hire boards: who assesses a station, and how many candidate seats a plan covers.

`slots.assessor_user_id` names the assessor the schedule gives a station (display only; the
circuit's lead still runs it). `organizations.candidate_seats` is the contract's candidate count
for an employer's Plan line; null until platform staff set it.

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-11-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a5b6c7d8e9f0"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "slots",
        sa.Column("assessor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column("organizations", sa.Column("candidate_seats", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "candidate_seats")
    op.drop_column("slots", "assessor_user_id")
