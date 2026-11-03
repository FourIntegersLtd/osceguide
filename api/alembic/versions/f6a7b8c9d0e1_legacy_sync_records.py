"""Remember which legacy Firestore documents the nightly sync has copied.

Adds a table only. Row level security is enabled with no policies, like every table
(`tests/integration/test_every_table_has_rls.py`).

Revision ID: f6a7b8c9d0e1
Revises: 7b2f6a1d4e9c
Create Date: 2026-11-03
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "7b2f6a1d4e9c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "legacy_sync_records",
        sa.Column("collection", sa.String(length=120), nullable=False),
        sa.Column("doc_id", sa.String(length=300), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("collection", "doc_id", name=op.f("pk_legacy_sync_records")),
    )
    op.execute("ALTER TABLE legacy_sync_records ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("legacy_sync_records")
