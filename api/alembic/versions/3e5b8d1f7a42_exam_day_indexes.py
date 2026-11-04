"""Exam-day indexes, one live unstarted attempt per start, and database-wide timeouts.

Adds only. Indexes are built CONCURRENTLY (no write lock on a live table), so they run in an
autocommit block, outside the migration's transaction; `IF NOT EXISTS` makes a retry after a
half-built (invalid) index safe only after it is dropped, which downgrade does.

The one data step first: duplicate unstarted attempts for the same start are failed with
`duplicate_start` (the newest is kept), so the unique index can be built.

The timeouts apply to NEW connections only. `pg_dump` sets its own `statement_timeout=0`. A long
job calls `core.jobs.allow_long_statement`; alembic sets `statement_timeout = 0` itself.

Revision ID: 3e5b8d1f7a42
Revises: f6a7b8c9d0e1
Create Date: 2026-11-04
"""

from __future__ import annotations

from alembic import op

revision = "3e5b8d1f7a42"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None

_UNSTARTED = (
    "status = 'created' AND started_at IS NULL AND definition_frozen_at IS NULL AND room_name IS NULL "
    "AND station_version_id IS NOT NULL AND kind IN ('practice', 'set_station', 'self_practice')"
)

INDEXES: dict[str, str] = {
    "ix_payments_user_id": "payments (user_id)",
    "ix_refresh_chains_user_id": "refresh_chains (user_id)",
    "ix_entitlements_user_id": "entitlements (user_id)",
    "ix_circuits_sitting_id": "circuits (sitting_id)",
    "ix_circuit_trainees_trainee_id": "circuit_trainees (trainee_id)",
    "ix_slots_org_circuit": "slots (org_id, circuit_id)",
    "ix_attempts_set_entry_id": "attempts (set_entry_id) WHERE set_entry_id IS NOT NULL",
    "ix_attempts_peer_session_id": "attempts (peer_session_id) WHERE peer_session_id IS NOT NULL",
    "ix_attempts_source_attempt_id": "attempts (source_attempt_id) WHERE source_attempt_id IS NOT NULL",
    "ix_candidate_result_revisions_org_released": (
        "candidate_result_revisions (org_id, sitting_id) WHERE released_at IS NOT NULL"
    ),
    "ix_stations_library": (
        "stations (exam_id, created_at, id) "
        "WHERE owner_kind = 'platform' AND status = 'published' AND approved"
    ),
    "ix_station_versions_station_published": "station_versions (station_id, published_at)",
}

UNIQUE_UNSTARTED = (
    "uq_attempts_one_unstarted",
    "attempts (user_id, kind, exam_id, org_id, station_version_id, set_entry_id) "
    f"NULLS NOT DISTINCT WHERE {_UNSTARTED}",
)


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE attempts SET status = 'failed', failed_reason = 'duplicate_start'
        WHERE id IN (
            SELECT id FROM (
                SELECT id, row_number() OVER (
                    PARTITION BY user_id, kind, exam_id, org_id, station_version_id, set_entry_id
                    ORDER BY created_at DESC, id DESC
                ) AS n
                FROM attempts WHERE {_UNSTARTED}
            ) ranked WHERE n > 1
        )
        """
    )
    with op.get_context().autocommit_block():
        for name, definition in INDEXES.items():
            op.execute(f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} ON {definition}")
        # NULLS NOT DISTINCT needs Postgres 15+; the clause sits before the column list's WHERE.
        op.execute(
            "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_attempts_one_unstarted ON attempts "
            "(user_id, kind, exam_id, org_id, station_version_id, set_entry_id) "
            f"NULLS NOT DISTINCT WHERE {_UNSTARTED}"
        )
    with op.get_context().autocommit_block():
        op.execute(
            "DO $$ BEGIN "
            "EXECUTE format('ALTER DATABASE %I SET statement_timeout = %L', current_database(), '15s'); "
            "EXECUTE format('ALTER DATABASE %I SET idle_in_transaction_session_timeout = %L', "
            "current_database(), '60s'); END $$"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "DO $$ BEGIN "
            "EXECUTE format('ALTER DATABASE %I RESET statement_timeout', current_database()); "
            "EXECUTE format('ALTER DATABASE %I RESET idle_in_transaction_session_timeout', "
            "current_database()); END $$"
        )
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS uq_attempts_one_unstarted")
        for name in INDEXES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
