"""Somewhere for a message from the public site to land.

Two forms in the retiring client had nowhere to go. `/messages` was the contact
form and the landing page's "Help Us Improve" section was product feedback;
neither reached a backend on this platform, so the first was not ported and the
second was left out of the landing sections rather than shipped as a form that
throws its input away.

One table with a `kind`, not two, because they are the same shape — and they
are read by different people, which is what the kind is for.

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-09-19 00:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4d5e6f7a8b9"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "site_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("email", postgresql.CITEXT(), nullable=True),
        sa.Column("subject", sa.String(length=200), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(length=200), nullable=True),
        sa.Column("handled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("handled_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_site_messages_user_id_users", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["handled_by"], ["users.id"], name="fk_site_messages_handled_by_users", ondelete="SET NULL"
        ),
    )
    op.create_check_constraint(
        "ck_site_messages_kind",
        "site_messages",
        "kind IN ('contact', 'product_feedback')",
    )
    # The inbox reads one kind at a time, newest first.
    op.create_index("ix_site_messages_kind_created", "site_messages", ["kind", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_site_messages_kind_created", table_name="site_messages")
    op.drop_table("site_messages")
