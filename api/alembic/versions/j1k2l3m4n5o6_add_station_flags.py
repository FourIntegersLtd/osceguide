"""Reports that a station is wrong, as rows rather than as a bookmark list.

The retiring client appended `{station_id, mock_id, flagged: true}` to the
user's own document, so the content team never saw a single one. This is the
table that makes the button in the runner mean something: one row per
(station, person), with a status staff can move.

No rows back. The legacy `flagged_stations` arrays were a reader's shortlist of
cases to revisit, not reports about a station's content, and importing them
would put words in the mouth of people who never filed a report.
"""

import sqlalchemy as sa
from alembic import op

revision = "j1k2l3m4n5o6"
down_revision = "i0j1k2l3m4n5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "station_flags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("station_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'open'"), nullable=False),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["station_id"], ["stations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("station_id", "user_id", name="uq_station_flags_station_user"),
        sa.CheckConstraint("status IN ('open', 'resolved')", name="ck_station_flags_status"),
    )
    op.create_index("ix_station_flags_status_created_at", "station_flags", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_station_flags_status_created_at", table_name="station_flags")
    op.drop_table("station_flags")
