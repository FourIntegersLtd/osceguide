"""Indexes for the list endpoints that moved their search/filter to the server.

Each of these backs a `WHERE`/`JOIN` the frontend used to run in the browser:
`attempts.exam_id` for `/me/attempts?search=`, `stations(org_id, status)` for
`include_archived=false`, `station_template_versions(template_id, status)` for
`published_only`, and `(status, starts_at)` on the two marketplace tables for
`status`/`when`. Plain B-tree indexes, not `pg_trgm`: the `ILIKE` searches
these endpoints also added (title, email, name) stay full-text-unindexed for
now — a trigram extension is a separate decision, not bundled into this one.
"""

import sqlalchemy as sa
from alembic import op

revision = "t1u2v3w4x5y6"
down_revision = "ef4595b78935"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_attempts_exam_id", "attempts", ["exam_id"])
    op.create_index("ix_stations_org_status", "stations", ["org_id", "status"])
    op.create_index(
        "ix_station_template_versions_template_status",
        "station_template_versions",
        ["template_id", "status"],
    )
    op.create_index(
        "ix_availability_posts_status_starts_at",
        "availability_posts",
        ["status", "starts_at"],
    )
    op.create_index(
        "ix_peer_sessions_status_starts_at",
        "peer_sessions",
        ["status", "starts_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_peer_sessions_status_starts_at", table_name="peer_sessions")
    op.drop_index("ix_availability_posts_status_starts_at", table_name="availability_posts")
    op.drop_index("ix_station_template_versions_template_status", table_name="station_template_versions")
    op.drop_index("ix_stations_org_status", table_name="stations")
    op.drop_index("ix_attempts_exam_id", table_name="attempts")
