"""Let a stranded outbox claim be taken back.

`claim_due` flips a message to `processing`, and the due index only sees
`pending`. A worker that died between claiming and sending left the message
invisible to every later query, with no timestamp to judge it by and no reaper.
An email nobody will ever send is worse than one sent twice.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-17 11:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "outbound_messages", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        op.f("ix_outbound_messages_claimed"),
        "outbound_messages",
        ["claimed_at"],
        postgresql_where=sa.text("status = 'processing'"),
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_outbound_messages_claimed"), table_name="outbound_messages")
    op.drop_column("outbound_messages", "claimed_at")
