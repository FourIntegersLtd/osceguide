"""Let a learner flag a station in one of their practice sets to come back to.

The retiring client kept `{station_id, mock_id, flagged}` on the user's own
document and listed it as "Flagged Stations". `station_flags` took over the
report-to-the-content-team half of that; this is the personal half, stored on
the set entry because a set has one owner and the flag is theirs alone.
"""

import sqlalchemy as sa
from alembic import op

revision = "927accf8f4db"
down_revision = "029f2c0b1966"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("station_set_entries", sa.Column("flagged_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_station_set_entries_flagged",
        "station_set_entries",
        ["set_id"],
        postgresql_where=sa.text("flagged_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_station_set_entries_flagged", table_name="station_set_entries")
    op.drop_column("station_set_entries", "flagged_at")
