"""Circuits remember a voice fault (R-16). Additive: one nullable column.

Revision ID: c7d8e9f0a1b2
Revises: afe3dcb4f06b
Create Date: 2026-10-08 09:30:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c7d8e9f0a1b2"
down_revision: str | None = "afe3dcb4f06b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("circuits", sa.Column("voice_fault_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("circuits", "voice_fault_at")
