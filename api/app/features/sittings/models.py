"""Tables owned by `sittings`. These classes never leave this slice's repository."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Revisioned, Timestamps, UUIDPrimaryKey


class Sitting(Base, UUIDPrimaryKey, Timestamps, Revisioned):
    """A scheduled event an organisation holds."""

    __tablename__ = "sittings"
    __table_args__ = (Index("ix_sittings_org_status", "org_id", "status"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    programme_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("org_programmes.id", ondelete="SET NULL")
    )
    cohort_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cohorts.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'training'"))
    sitting_type: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'group_training'")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'scheduled'"))
    rubric_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rubric_versions.id", ondelete="RESTRICT"), nullable=False
    )


class Circuit(Base, UUIDPrimaryKey, Timestamps, Revisioned):
    """A group or a single candidate running through a set of stations, with its own clock."""

    __tablename__ = "circuits"
    __table_args__ = (
        # The exam-day board asks this of every organisation whenever anything
        # changes, and a live circuit is a vanishing fraction of the table.
        Index(
            "ix_circuits_live",
            "org_id",
            postgresql_where=text("started_at IS NOT NULL AND ended_at IS NULL"),
        ),
        Index(
            "ix_circuits_sitting_id",
            "sitting_id",
            postgresql_concurrently=True,
        ),
    )

    sitting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sittings.id", ondelete="CASCADE"), nullable=False
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    supervisor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # A closed shape with a handful of fields, kept as JSON because the break
    # list is variable-length and read as a unit.
    timing: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    active_slot_id: Mapped[uuid.UUID | None] = mapped_column()
    room_name: Mapped[str | None] = mapped_column(String(200))
    agent_dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # The examination clock. It sits here rather than on the slot because a
    # break belongs to no slot, and because pausing must rewrite one deadline
    # rather than two (D-6).
    phase: Mapped[str | None] = mapped_column(String(16))
    phase_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    phase_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Bumped by every transition and every override. A scheduled transition
    # carries the sequence it was scheduled against and does nothing if it no
    # longer matches, which is how a human's intervention beats the clock.
    phase_seq: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paused_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    auto_advance: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    # R-16: when the voice service last refused to bring the patient in. Set by the
    # automatic advance that failed, cleared by the step that finally succeeds.
    voice_fault_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CircuitStation(Base, UUIDPrimaryKey):
    """A real row per station, so a station cannot be deleted out from under a
    circuit and "which circuits use this station?" is a query."""

    __tablename__ = "circuit_stations"
    __table_args__ = (
        UniqueConstraint("circuit_id", "position", name="uq_circuit_stations_circuit_position"),
    )

    circuit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("circuits.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    station_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("station_versions.id", ondelete="RESTRICT"), nullable=False
    )


class CircuitTrainee(Base, UUIDPrimaryKey):
    """One trainee's membership of a circuit, before or after they have a slot."""

    __tablename__ = "circuit_trainees"
    __table_args__ = (
        UniqueConstraint("circuit_id", "trainee_id", name="uq_circuit_trainees_circuit_trainee"),
        Index(
            "ix_circuit_trainees_trainee_id",
            "trainee_id",
            postgresql_concurrently=True,
        ),
    )

    circuit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("circuits.id", ondelete="CASCADE"), nullable=False
    )
    trainee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class Slot(Base, UUIDPrimaryKey, Timestamps):
    """One trainee at one station.

    Carries no transcript and no feedback: those live on the attempt, which is
    what makes a re-dispatch keep the first recording instead of overwriting it.
    Carries no clock either — that is the circuit's, because a break belongs to
    no slot and a pause must move one deadline rather than two.

    The id is globally unique because the worker and several routes address a
    slot directly; every user-facing route still resolves `org_id` from the row.
    """

    __tablename__ = "slots"
    __table_args__ = (
        UniqueConstraint("circuit_id", "slot_index", name="uq_slots_circuit_index"),
        Index("ix_slots_org_status", "org_id", "status"),
        Index("ix_slots_trainee", "trainee_id"),
        Index(
            "ix_slots_org_circuit",
            "org_id",
            "circuit_id",
            postgresql_concurrently=True,
        ),
    )

    circuit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("circuits.id", ondelete="CASCADE"), nullable=False
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    slot_index: Mapped[int] = mapped_column(Integer, nullable=False)
    trainee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    station_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("station_versions.id", ondelete="RESTRICT"), nullable=False
    )
    # scheduled → reading → in_consultation → completed, or skipped if the
    # circuit moved past it.
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'scheduled'"))
    room_name: Mapped[str | None] = mapped_column(String(200))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exam_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CircuitIntervention(Base, UUIDPrimaryKey):
    """What a human did to a running examination, and why.

    Append-only, and no `updated_at`: an intervention is a fact about a moment,
    not a row anybody edits.
    """

    __tablename__ = "circuit_interventions"
    __table_args__ = (Index("ix_circuit_interventions_circuit", "circuit_id", "at"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    circuit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("circuits.id", ondelete="CASCADE"), nullable=False
    )
    # Null for an override about the circuit rather than one station.
    slot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("slots.id", ondelete="SET NULL"))
    # SET NULL, not CASCADE: removing a member must not delete the record that
    # they extended a candidate's clock.
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    phase_seq_before: Mapped[int] = mapped_column(Integer, nullable=False)
    phase_seq_after: Mapped[int] = mapped_column(Integer, nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CircuitRunHistory(Base, UUIDPrimaryKey):
    """One finished run of a circuit, as the exam-day board last saw it.

    Written once, in the same transaction that ends the circuit, and never
    edited. The circuit row keeps changing meaning after it ends (its slots can
    be rescued, the circuit or its sitting deleted); this is what the day
    actually looked like when it stopped. Field names follow the live board's.
    """

    __tablename__ = "circuit_run_history"
    __table_args__ = (
        UniqueConstraint("circuit_id", "ended_at", name="uq_circuit_run_history_circuit_ended"),
        Index("ix_circuit_run_history_org_ended", "org_id", "ended_at"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    # SET NULL rather than CASCADE: deleting a circuit or a sitting afterwards
    # must not rewrite what happened on the day.
    circuit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("circuits.id", ondelete="SET NULL"))
    sitting_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sittings.id", ondelete="SET NULL"))
    circuit_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sitting_name: Mapped[str] = mapped_column(String(200), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    supervisor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    stations_total: Mapped[int] = mapped_column(Integer, nullable=False)
    stations_completed: Mapped[int] = mapped_column(Integer, nullable=False)
    # `completed` when every station was sat, `ended_early` when any was skipped.
    status: Mapped[str] = mapped_column(String(16), nullable=False)
