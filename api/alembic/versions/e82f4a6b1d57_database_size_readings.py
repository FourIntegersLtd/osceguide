"""One row a day of how big the database is, for the Ops forecast.

Adds a table only. Row level security is enabled with no policies, like every table
(`tests/integration/test_every_table_has_rls.py`).

Revision ID: e82f4a6b1d57
Revises: c47a1e6d9b30
Create Date: 2026-10-31
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e82f4a6b1d57"
down_revision = "c47a1e6d9b30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "database_size_readings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("taken_on", sa.Date(), nullable=False),
        sa.Column("total_bytes", sa.BigInteger(), nullable=False),
        sa.Column("relations", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("alert_level", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_database_size_readings")),
        sa.UniqueConstraint("taken_on", name="uq_database_size_readings_taken_on"),
    )
    op.execute("ALTER TABLE database_size_readings ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("database_size_readings")
