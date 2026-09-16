"""Tables owned by `peer_practice`."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class QueueEntry(Base, UUIDPrimaryKey, Timestamps):
    """Someone waiting to be paired."""

    __tablename__ = "practice_queue_entries"
    __table_args__ = (
        # One live place in the queue per person per exam; joining twice keeps
        # the place you already have.
        Index(
            "uq_practice_queue_live",
            "user_id",
            "exam_id",
            unique=True,
            postgresql_where=text("status = 'waiting'"),
        ),
        Index(
            "ix_practice_queue_waiting",
            "exam_id",
            "created_at",
            postgresql_where=text("status = 'waiting'"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'waiting'"))
    matched_session_id: Mapped[uuid.UUID | None] = mapped_column()
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PracticeSession(Base, UUIDPrimaryKey, Timestamps):
    """Two people practising, one as doctor and one as patient."""

    __tablename__ = "practice_sessions"
    __table_args__ = (Index("ix_practice_sessions_participants", "doctor_user_id", "patient_user_id"),)

    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False)
    doctor_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    patient_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    station_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("station_versions.id", ondelete="SET NULL")
    )
    room_name: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'matched'"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_reason: Mapped[str | None] = mapped_column(String(32))


class PracticeHistory(Base, UUIDPrimaryKey, Timestamps):
    """What part someone last played, and how often they have practised.

    A row rather than fields on the user: it is peer-practice's business, and
    b2c putting it on the user document is why the matcher reaches into four
    different collections to find it.
    """

    __tablename__ = "practice_history"
    __table_args__ = (Index("uq_practice_history_user", "user_id", unique=True),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    last_role: Mapped[str | None] = mapped_column(String(16))
    session_count: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    # Replaces b2c's hardcoded list of three personal email addresses.
    never_doctor: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
