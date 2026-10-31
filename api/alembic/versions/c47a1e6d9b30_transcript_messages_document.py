"""Transcript turns as one document on the transcripts row.

Two nullable columns, so the release before this runs against the new schema unchanged.
`messages` holds a finished attempt's turns as one document ({"v": 1, "turns": [...]}) and
`message_count` how many there are; both stay NULL while the turns are `transcript_messages` rows.
The `compact_transcripts` job fills them and deletes the rows.

Revision ID: c47a1e6d9b30
Revises: 4f1c7e92a6d0
Create Date: 2026-10-31
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c47a1e6d9b30"
down_revision = "4f1c7e92a6d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("transcripts", sa.Column("messages", postgresql.JSONB(), nullable=True))
    op.add_column("transcripts", sa.Column("message_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("transcripts", "message_count")
    op.drop_column("transcripts", "messages")
