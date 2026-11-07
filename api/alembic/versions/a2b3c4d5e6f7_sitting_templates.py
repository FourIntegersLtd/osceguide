"""Sitting templates: a named setup an organisation starts new schedules from.

Adds only.

Revision ID: a2b3c4d5e6f7
Revises: e3f4a5b6c7d8
Create Date: 2026-11-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a2b3c4d5e6f7"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sitting_templates",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name="fk_sitting_templates_org_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_sitting_templates_created_by_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sitting_templates"),
    )
    # Every table has RLS on (tests/integration/test_every_table_has_rls.py); the app role bypasses it.
    op.execute("ALTER TABLE sitting_templates ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE UNIQUE INDEX uq_sitting_templates_org_name ON sitting_templates (org_id, lower(name))")


def downgrade() -> None:
    op.drop_table("sitting_templates")
