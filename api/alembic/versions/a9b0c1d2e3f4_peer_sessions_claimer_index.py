"""Index peer_sessions.claimer_user_id for claimer-side lookups.

The participants index leads with owner_user_id; sessions for one claimer alone
did not use it efficiently.

Revision ID: a9b0c1d2e3f4
Revises: 3e5b8d1f7a42
Create Date: 2026-11-05
"""

from __future__ import annotations

from alembic import op

revision = "a9b0c1d2e3f4"
down_revision = "3e5b8d1f7a42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_peer_sessions_claimer_user_id "
            "ON peer_sessions (claimer_user_id)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_peer_sessions_claimer_user_id")
