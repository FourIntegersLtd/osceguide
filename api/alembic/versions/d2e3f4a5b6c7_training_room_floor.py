"""A training circuit's room: whether the floor is open and when the supervisor closed it.

`open_floor` lets every participant speak (the end-of-session conversation).
`room_closed_at` is when the supervisor closed a training room that stayed open after End.

Revision ID: d2e3f4a5b6c7
Revises: b0c1d2e3f4a5
Create Date: 2026-11-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d2e3f4a5b6c7"
down_revision = "b0c1d2e3f4a5"
branch_labels = None
depends_on = None


# Circuits that ended before this change have no room to keep: mark them closed, so a past
# practice circuit is not "kept open" (joinable, tokens issued).
BACKFILL_SQL = "UPDATE circuits SET room_closed_at = ended_at WHERE ended_at IS NOT NULL"


def upgrade() -> None:
    op.add_column("circuits", sa.Column("open_floor", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("circuits", sa.Column("room_closed_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(BACKFILL_SQL)


def downgrade() -> None:
    op.drop_column("circuits", "room_closed_at")
    op.drop_column("circuits", "open_floor")
