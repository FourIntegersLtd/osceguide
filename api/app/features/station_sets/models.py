"""Tables owned by `station_sets`. These classes never leave this slice's repository."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class StationSet(Base, UUIDPrimaryKey, Timestamps):
    """A learner's own collection of stations to practise."""

    __tablename__ = "station_sets"
    __table_args__ = (Index("ix_station_sets_owner", "owner_user_id", "created_at"),)

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Locked rather than deleted when access lapses, so the work reappears on
    # renewal instead of vanishing.
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StationSetEntry(Base, UUIDPrimaryKey, Timestamps):
    """One station inside a set, with how often it has been run.

    The counters are the reason a set is not a circuit: a slot is sat once.
    """

    __tablename__ = "station_set_entries"
    __table_args__ = (
        UniqueConstraint("set_id", "position", name="uq_station_set_entries_set_position"),
        # "My flagged stations" reads only flagged rows, which are few.
        Index("ix_station_set_entries_flagged", "set_id", postgresql_where=text("flagged_at IS NOT NULL")),
    )

    set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("station_sets.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    station_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("station_versions.id", ondelete="RESTRICT"), nullable=False
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    debrief_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # When the owner flagged this station to come back to, or null. Personal:
    # a report to the content team is a `station_flags` row instead.
    flagged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
