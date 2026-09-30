"""Make an attempt's references real, and its status a closed set.

`slot_id`, `set_entry_id` and `peer_session_id` were bare uuid columns: the
CHECK said which one a kind must carry, and nothing said the row it named had
to exist. A deleted slot left orphaned attempts pointing at nothing.

`RESTRICT`, not `CASCADE`: an attempt is the recording of something that
happened to a person, and deleting the slot it belonged to must not take the
transcript with it. Nothing deletes slots today — the two repository functions
that did had no callers and are gone with this — so restricting costs nothing
and states the rule.

`attempts.status` gains the vocabulary `domain.Status` already had. The other
status columns are deliberately left alone: only `scheduled` and `in_progress`
are ever written for a sitting and nothing writes a slot status at all, so a
CHECK there would be inventing a product decision rather than recording one.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-17 11:30:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = "('created', 'running', 'interaction_complete', 'evaluated', 'failed')"


def upgrade() -> None:
    # Orphans first: a reference to a row that is already gone cannot become a
    # foreign key. There should be none, and if there are, this says so rather
    # than failing on the constraint with no explanation.
    for column, table in (
        ("slot_id", "slots"),
        ("set_entry_id", "station_set_entries"),
        ("peer_session_id", "practice_sessions"),
    ):
        op.execute(
            sa.text(
                f"UPDATE attempts SET {column} = NULL WHERE {column} IS NOT NULL "
                f"AND NOT EXISTS (SELECT 1 FROM {table} t WHERE t.id = attempts.{column})"
                " AND kind NOT IN ('exam_slot', 'set_station', 'peer')"
            )
        )

    op.create_foreign_key(
        op.f("fk_attempts_slot_id_slots"), "attempts", "slots", ["slot_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_foreign_key(
        op.f("fk_attempts_set_entry_id_station_set_entries"),
        "attempts",
        "station_set_entries",
        ["set_entry_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_attempts_peer_session_id_practice_sessions"),
        "attempts",
        "practice_sessions",
        ["peer_session_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_sittings_cohort_id_cohorts"),
        "sittings",
        "cohorts",
        ["cohort_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(op.f("ck_attempts_ck_attempts_status"), "attempts", f"status IN {STATUSES}")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_attempts_ck_attempts_status"), "attempts", type_="check")
    op.drop_constraint(op.f("fk_sittings_cohort_id_cohorts"), "sittings", type_="foreignkey")
    op.drop_constraint(
        op.f("fk_attempts_peer_session_id_practice_sessions"), "attempts", type_="foreignkey"
    )
    op.drop_constraint(
        op.f("fk_attempts_set_entry_id_station_set_entries"), "attempts", type_="foreignkey"
    )
    op.drop_constraint(op.f("fk_attempts_slot_id_slots"), "attempts", type_="foreignkey")
