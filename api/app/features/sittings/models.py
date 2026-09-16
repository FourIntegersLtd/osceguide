"""Tables owned by `sittings`. These classes never leave this slice's repository."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class Sitting(Base, UUIDPrimaryKey, Timestamps):
    """A scheduled event an organisation holds."""

    __tablename__ = "sittings"
    __table_args__ = (Index("ix_sittings_org_status", "org_id", "status"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    programme_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("org_programmes.id", ondelete="SET NULL")
    )
    cohort_id: Mapped[uuid.UUID | None] = mapped_column()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'training'"))
    sitting_type: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'group_training'")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'scheduled'"))
    # Not null: b2b refuses to create a session without a published feedback
    # template bound, and the column says so rather than a service check.
    feedback_template_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feedback_template_versions.id", ondelete="RESTRICT"), nullable=False
    )


class Circuit(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "circuits"

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


class CircuitStation(Base, UUIDPrimaryKey):
    """Replaces b2b's `station_refs jsonb`.

    A real row per station, so a station cannot be deleted out from under a
    circuit and "which circuits use this station?" is a query.
    """

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
    """Replaces b2b's `trainee_ids text[]`."""

    __tablename__ = "circuit_trainees"
    __table_args__ = (
        UniqueConstraint("circuit_id", "trainee_id", name="uq_circuit_trainees_circuit_trainee"),
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
    The id is globally unique because the worker and several routes address a
    slot directly; every user-facing route still resolves `org_id` from the row.
    """

    __tablename__ = "slots"
    __table_args__ = (
        UniqueConstraint("circuit_id", "slot_index", name="uq_slots_circuit_index"),
        Index("ix_slots_org_status", "org_id", "status"),
        Index("ix_slots_trainee", "trainee_id"),
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
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'scheduled'"))
    room_name: Mapped[str | None] = mapped_column(String(200))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exam_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Nullable and unused until D-6 is settled. The exam clock currently lives
    # in the supervisor's browser and is lost on refresh; these columns exist so
    # server-owned timing needs no migration once that is decided.
    phase: Mapped[str | None] = mapped_column(String(16))
    phase_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    phase_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
