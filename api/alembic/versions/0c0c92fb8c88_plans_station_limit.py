"""How many library stations a plan unlocks; empty means every station.

Revision ID: 0c0c92fb8c88
Revises: a1c4e7f2b930
Create Date: 2026-11-01 00:00:00+00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0c0c92fb8c88"
down_revision = "a1c4e7f2b930"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the nullable station-limit column to `plans`. NULL means no limit."""
    op.add_column("plans", sa.Column("station_limit", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Drop the station-limit column."""
    op.drop_column("plans", "station_limit")
