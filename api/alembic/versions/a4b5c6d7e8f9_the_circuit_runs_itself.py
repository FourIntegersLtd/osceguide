"""Move the examination clock onto the circuit, so it can run itself.

The clock lived on the slot, and only a human ever wrote it: a supervisor
switched the turn and it became `reading`, dispatched the patient and it became
`simulation`. Nothing read `phase_ends_at` server-side, so nothing happened when
it passed. A real OSCE runs on a bell.

Three things had to move for the bell to exist.

**The clock belongs to the circuit, not the slot.** A break is the circuit
resting between stations — there is no slot it belongs to — and it is the one
thing the per-slot clock could not express, which is why breaks were stored and
counted down by nobody. A pause has the same shape: stopping the clock must
rewrite one deadline, and with the clock on two rows it rewrote two. The slot
columns are dropped rather than mirrored, because a mirror is exactly the two
clocks D-6 removed. Screens still show a phase against the active slot; they
derive it from the circuit.

**`phase_seq` is how a human beats the clock.** Every transition is a job
scheduled for the moment the phase ends, carrying the sequence it was scheduled
against. Any override bumps the sequence, so the job it raced arrives holding a
number that no longer matches and does nothing. That is the whole concurrency
design: no lease, no claim table, one integer.

**A slot's status becomes true.** `status`, `started_at`, `ended_at` and
`exam_completed_at` were written by nothing and displayed by four read models.
The orchestrator owns them now, and the check constraint says what they may be.

`circuit_interventions` records every override. When a candidate says their
station went wrong, the question is what was done to it and by whom, and the
answer was previously nowhere.

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-09-18 00:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a4b5c6d7e8f9"
down_revision: str | None = "f3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ---- the clock moves onto the circuit -------------------------------
    op.add_column("circuits", sa.Column("phase", sa.String(length=16), nullable=True))
    op.add_column("circuits", sa.Column("phase_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("circuits", sa.Column("phase_ends_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "circuits",
        sa.Column("phase_seq", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column("circuits", sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "circuits",
        sa.Column("paused_seconds", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "circuits",
        sa.Column("auto_advance", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_check_constraint(
        "ck_circuits_phase",
        "circuits",
        "phase IS NULL OR phase IN ('reading', 'simulation', 'break')",
    )

    # The live board asks this of every organisation, every few seconds, and a
    # live circuit is a vanishing fraction of the table.
    op.create_index(
        "ix_circuits_live",
        "circuits",
        ["org_id"],
        postgresql_where=sa.text("started_at IS NOT NULL AND ended_at IS NULL"),
    )

    # ---- and off the slot ------------------------------------------------
    op.drop_column("slots", "phase")
    op.drop_column("slots", "phase_started_at")
    op.drop_column("slots", "phase_ends_at")

    # Written by nothing until now, so every existing row is 'scheduled' and
    # the constraint cannot fail on data already there.
    op.create_check_constraint(
        "ck_slots_status",
        "slots",
        "status IN ('scheduled', 'reading', 'in_consultation', 'completed', 'skipped')",
    )

    # ---- what a human did to a running examination ------------------------
    op.create_table(
        "circuit_interventions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "circuit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("circuits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Null for an override that is about the circuit rather than one
        # station: a pause, a resume, the end of the whole thing.
        sa.Column(
            "slot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("slots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # SET NULL rather than CASCADE: deleting a member must not delete the
        # record that they extended a candidate's clock.
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        # The sequence either side, so a reader can place the intervention
        # against the transition it displaced.
        sa.Column("phase_seq_before", sa.Integer(), nullable=False),
        sa.Column("phase_seq_after", sa.Integer(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_circuit_interventions_circuit", "circuit_interventions", ["circuit_id", "at"])


def downgrade() -> None:
    op.drop_index("ix_circuit_interventions_circuit", table_name="circuit_interventions")
    op.drop_table("circuit_interventions")

    op.drop_constraint("ck_slots_status", "slots", type_="check")
    # Re-added nullable and empty. A circuit mid-examination cannot be
    # downgraded into: the clock it is running on would be gone.
    op.add_column("slots", sa.Column("phase", sa.String(length=16), nullable=True))
    op.add_column("slots", sa.Column("phase_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("slots", sa.Column("phase_ends_at", sa.DateTime(timezone=True), nullable=True))

    op.drop_index("ix_circuits_live", table_name="circuits")
    op.drop_constraint("ck_circuits_phase", "circuits", type_="check")
    for column in (
        "auto_advance",
        "paused_seconds",
        "paused_at",
        "phase_seq",
        "phase_ends_at",
        "phase_started_at",
        "phase",
    ):
        op.drop_column("circuits", column)
