"""Per-station assessors and a staggered start offset on a circuit.

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-11-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f4a5b6c7d8e9"
down_revision = "c4a9e1d27b30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "circuits",
        sa.Column("start_offset_minutes", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column("circuits", sa.Column("station_assessors", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("circuits", "station_assessors")
    op.drop_column("circuits", "start_offset_minutes")
