"""Appeals against a released result, an organisation's retention choice, and the erasure marker.

Revision ID: c4a9e1d27b30
Revises: e3f4a5b6c7d8
Create Date: 2026-11-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c4a9e1d27b30"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("recording_retention_days", sa.Integer(), nullable=True))
    op.add_column("attempts", sa.Column("content_erased_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "result_appeals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sitting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sittings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trainee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trainees.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("outcome_revision", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'open'")),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("on_behalf", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('open', 'in_review', 'resolved', 'declined')", name="ck_result_appeals_status"),
        sa.CheckConstraint("status <> 'in_review' OR assigned_to IS NOT NULL", name="ck_result_appeals_assigned"),
    )
    op.create_index(
        "uq_result_appeals_active",
        "result_appeals",
        ["sitting_id", "trainee_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('open', 'in_review')"),
    )
    op.create_index("ix_result_appeals_org_status", "result_appeals", ["org_id", "status"])
    op.execute("ALTER TABLE result_appeals ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("result_appeals")
    op.drop_column("attempts", "content_erased_at")
    op.drop_column("organizations", "recording_retention_days")
