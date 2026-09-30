"""peer practice b2c parity fields

Revision ID: g8h9i0j1k2l3
Revises: f7a8b9c0d1e2
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "g8h9i0j1k2l3"
down_revision: str | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "practice_queue_entries",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("practice_sessions", sa.Column("peer_session_id", sa.Uuid(), nullable=True))
    op.add_column("practice_sessions", sa.Column("current_phase", sa.String(length=16), nullable=True))
    op.add_column("practice_sessions", sa.Column("phase_ends_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("practice_sessions", sa.Column("doctor_joined_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("practice_sessions", sa.Column("patient_joined_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "practice_sessions", sa.Column("preparation_started_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("practice_sessions", sa.Column("feedback_rating", sa.Integer(), nullable=True))
    op.add_column("practice_sessions", sa.Column("feedback_comment", sa.String(length=2000), nullable=True))
    op.create_foreign_key(
        op.f("fk_practice_sessions_peer_session_id_peer_sessions"),
        "practice_sessions",
        "peer_sessions",
        ["peer_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("peer_sessions", sa.Column("practice_session_id", sa.Uuid(), nullable=True))
    op.add_column("peer_sessions", sa.Column("doctor_user_id", sa.Uuid(), nullable=True))
    op.add_column("peer_sessions", sa.Column("patient_user_id", sa.Uuid(), nullable=True))
    op.add_column("peer_sessions", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        op.f("fk_peer_sessions_practice_session_id_practice_sessions"),
        "peer_sessions",
        "practice_sessions",
        ["practice_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("fk_peer_sessions_doctor_user_id_users"),
        "peer_sessions",
        "users",
        ["doctor_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("fk_peer_sessions_patient_user_id_users"),
        "peer_sessions",
        "users",
        ["patient_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_peer_sessions_patient_user_id_users"), "peer_sessions", type_="foreignkey")
    op.drop_constraint(op.f("fk_peer_sessions_doctor_user_id_users"), "peer_sessions", type_="foreignkey")
    op.drop_constraint(
        op.f("fk_peer_sessions_practice_session_id_practice_sessions"), "peer_sessions", type_="foreignkey"
    )
    op.drop_column("peer_sessions", "cancelled_at")
    op.drop_column("peer_sessions", "patient_user_id")
    op.drop_column("peer_sessions", "doctor_user_id")
    op.drop_column("peer_sessions", "practice_session_id")
    op.drop_constraint(
        op.f("fk_practice_sessions_peer_session_id_peer_sessions"), "practice_sessions", type_="foreignkey"
    )
    op.drop_column("practice_sessions", "feedback_comment")
    op.drop_column("practice_sessions", "feedback_rating")
    op.drop_column("practice_sessions", "preparation_started_at")
    op.drop_column("practice_sessions", "patient_joined_at")
    op.drop_column("practice_sessions", "doctor_joined_at")
    op.drop_column("practice_sessions", "phase_ends_at")
    op.drop_column("practice_sessions", "current_phase")
    op.drop_column("practice_sessions", "peer_session_id")
    op.drop_column("practice_queue_entries", "expires_at")
