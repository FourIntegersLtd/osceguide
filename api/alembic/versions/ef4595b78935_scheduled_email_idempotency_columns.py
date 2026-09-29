"""Idempotency columns for two scheduled emails ported from legacy `b2c-api`:
`peer_sessions.reminder_sent_at` (the marketplace "starts in an hour" reminder,
`marketplace.jobs.send_marketplace_session_reminders`) and
`users.engagement_email_sent_at` (the "come try a station" nudge,
`identity.jobs.send_engagement_emails`). Each is set once, by an atomic
`UPDATE ... WHERE ... IS NULL ... RETURNING`, so two workers polling at the
same moment can never both send the same email.

Revision ID: ef4595b78935
Revises: 181b027540b9
Create Date: 2026-09-29 13:35:21.501179+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ef4595b78935"
down_revision: str | None = "181b027540b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add both idempotency columns, each nullable so existing rows are
    simply "not yet sent" rather than requiring a backfill value."""
    op.add_column("peer_sessions", sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("engagement_email_sent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Drop both columns. Safe: neither is read by anything except the two
    jobs this revision exists for."""
    op.drop_column("users", "engagement_email_sent_at")
    op.drop_column("peer_sessions", "reminder_sent_at")
