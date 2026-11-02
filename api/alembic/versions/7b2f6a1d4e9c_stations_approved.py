"""An editor's approval gate on top of a station's publish status.

Mirrors legacy b2c's `approved` flag: a published station must now also be approved before a
normal reader of the library sees it. Every station already `published` as of this migration is
backfilled to `approved = true`, so nothing live goes dark; only a station that becomes
`published` after this ships starts out unapproved.

Revision ID: 7b2f6a1d4e9c
Revises: 0c0c92fb8c88
Create Date: 2026-11-02 00:00:00+00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "7b2f6a1d4e9c"
down_revision = "0c0c92fb8c88"
branch_labels = None
depends_on = None

# A module constant so a test can run the backfill against rows it wrote, same pattern as the
# media-specialty and never-doctor backfills.
BACKFILL_SQL = "UPDATE stations SET approved = true WHERE status = 'published'"


def upgrade() -> None:
    """Add `stations.approved`, defaulted false, then backfill already-published rows true."""
    op.add_column(
        "stations",
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute(BACKFILL_SQL)


def downgrade() -> None:
    """Drop the approval column; the publish/approve split goes with it."""
    op.drop_column("stations", "approved")
