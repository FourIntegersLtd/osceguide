"""Hire boards: how many candidate seats an employer's plan covers.

`organizations.candidate_seats` is the contract's candidate count for an employer's Plan line;
null until platform staff set it.

Revision ID: 9e4b2a7c5d18
Revises: b6c7d8e9f0a1
Create Date: 2026-11-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "9e4b2a7c5d18"
down_revision = "b6c7d8e9f0a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("candidate_seats", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "candidate_seats")
