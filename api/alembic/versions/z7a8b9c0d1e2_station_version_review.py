"""Keep a fact check of a platform station version beside its content.

A nullable column, so the release before this one runs against it unchanged.

Revision ID: z7a8b9c0d1e2
Revises: y6z7a8b9c0d1
Create Date: 2026-10-04 00:00:00+00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "z7a8b9c0d1e2"
down_revision = "y6z7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("station_versions", sa.Column("review", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("station_versions", "review")
