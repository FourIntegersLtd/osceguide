"""Non-verbal feedback: consent, per-second batches, summaries, and an organisation switch.

Adds three tables and one column. Row level security is enabled on each table with no policies, like
every table (`tests/integration/test_every_table_has_rls.py`).

Revision ID: ac5d1be76cd8
Revises: 9e4b2a7c5d18
Create Date: 2026-11-13 08:11:03.310917+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "ac5d1be76cd8"
down_revision: str | None = "9e4b2a7c5d18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "nonverbal_consents",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_nonverbal_consents_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_nonverbal_consents")),
    )
    op.create_table(
        "attempt_nonverbal_batches",
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("skew_ms", sa.BigInteger(), nullable=False),
        sa.Column("samples", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["attempts.id"],
            name=op.f("fk_attempt_nonverbal_batches_attempt_id_attempts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("attempt_id", "seq", name=op.f("pk_attempt_nonverbal_batches")),
    )
    op.create_table(
        "attempt_nonverbal_summaries",
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("facts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("feedback", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("model_used", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["attempts.id"],
            name=op.f("fk_attempt_nonverbal_summaries_attempt_id_attempts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("attempt_id", name=op.f("pk_attempt_nonverbal_summaries")),
    )
    for table in ("nonverbal_consents", "attempt_nonverbal_batches", "attempt_nonverbal_summaries"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.add_column(
        "organizations",
        sa.Column(
            "nonverbal_feedback_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("organizations", "nonverbal_feedback_enabled")
    op.drop_table("attempt_nonverbal_summaries")
    op.drop_table("attempt_nonverbal_batches")
    op.drop_table("nonverbal_consents")
