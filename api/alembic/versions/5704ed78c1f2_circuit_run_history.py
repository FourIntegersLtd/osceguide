"""A row per finished circuit run, for the exam-day board's history.

The board is built live from circuits that are running, so once a circuit
ended there was nothing to look back at. Written once when a circuit ends;
circuit and sitting keys are SET NULL so a later delete keeps the record.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "5704ed78c1f2"
down_revision: str | None = "927accf8f4db"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "circuit_run_history",
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("circuit_id", sa.Uuid(), nullable=True),
        sa.Column("sitting_id", sa.Uuid(), nullable=True),
        sa.Column("circuit_name", sa.String(length=200), nullable=False),
        sa.Column("sitting_name", sa.String(length=200), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("supervisor_user_id", sa.Uuid(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("stations_total", sa.Integer(), nullable=False),
        sa.Column("stations_completed", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["circuit_id"],
            ["circuits.id"],
            name=op.f("fk_circuit_run_history_circuit_id_circuits"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_circuit_run_history_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sitting_id"],
            ["sittings.id"],
            name=op.f("fk_circuit_run_history_sitting_id_sittings"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["supervisor_user_id"],
            ["users.id"],
            name=op.f("fk_circuit_run_history_supervisor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_circuit_run_history")),
        sa.UniqueConstraint("circuit_id", "ended_at", name="uq_circuit_run_history_circuit_ended"),
    )
    op.create_index(
        "ix_circuit_run_history_org_ended", "circuit_run_history", ["org_id", "ended_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_circuit_run_history_org_ended", table_name="circuit_run_history")
    op.drop_table("circuit_run_history")
