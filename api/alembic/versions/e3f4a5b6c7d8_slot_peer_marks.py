"""Peer marks: what a watching trainee marks on another trainee's turn.

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-11-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "slot_peer_marks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("circuit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("circuits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("slots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("marker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item", sa.String(160), nullable=False),
        sa.Column("rating", sa.String(16), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("circuit_id", "slot_id", "marker_id", "item", name="uq_slot_peer_marks_item"),
    )
    op.create_index("ix_slot_peer_marks_slot", "slot_peer_marks", ["org_id", "slot_id"])
    # Every table has RLS on (tests/integration/test_every_table_has_rls.py); the app role bypasses it.
    op.execute("ALTER TABLE slot_peer_marks ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_slot_peer_marks_slot", table_name="slot_peer_marks")
    op.drop_table("slot_peer_marks")
