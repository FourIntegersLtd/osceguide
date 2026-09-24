"""peer_practice_recording

Recording, transcription and the doctor's scored attempt for a peer session
(P-1). `attempts.peer_session_id` and `attempts.kind = 'peer'` already existed
and nothing wrote them; these are the columns the writing needs.

Revision ID: n5o6p7q8r9s0
Revises: 2b982c151fdf
Create Date: 2026-09-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "n5o6p7q8r9s0"
down_revision: str | None = "2b982c151fdf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("practice_sessions", sa.Column("egress_id", sa.String(length=128), nullable=True))
    op.add_column("practice_sessions", sa.Column("recording_key", sa.String(length=512), nullable=True))
    op.add_column(
        "practice_sessions",
        sa.Column(
            "recording_state",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'none'"),
        ),
    )
    op.add_column("practice_sessions", sa.Column("recording_error", sa.String(length=200), nullable=True))
    op.add_column(
        "practice_sessions",
        sa.Column("doctor_attempt_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # `use_alter` on the model side: `attempts` already carries a
    # `peer_session_id` pointing here, so the two tables reference each other
    # and the constraint cannot be created with the column.
    op.create_foreign_key(
        "fk_practice_sessions_doctor_attempt_id_attempts",
        "practice_sessions",
        "attempts",
        ["doctor_attempt_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # The transcription job finds its work by state, and the session read looks
    # up a doctor's attempt. Both are narrow slices of a growing table.
    op.create_index(
        "ix_practice_sessions_recording_state",
        "practice_sessions",
        ["recording_state"],
        postgresql_where=sa.text("recording_state <> 'none'"),
    )


def downgrade() -> None:
    op.drop_index("ix_practice_sessions_recording_state", table_name="practice_sessions")
    op.drop_constraint(
        "fk_practice_sessions_doctor_attempt_id_attempts", "practice_sessions", type_="foreignkey"
    )
    op.drop_column("practice_sessions", "doctor_attempt_id")
    op.drop_column("practice_sessions", "recording_error")
    op.drop_column("practice_sessions", "recording_state")
    op.drop_column("practice_sessions", "recording_key")
    op.drop_column("practice_sessions", "egress_id")
