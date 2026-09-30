"""Tables owned by `peer_practice`."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import AUDIENCE_CHECK, Addressed, Base, Timestamps, UUIDPrimaryKey


class QueueEntry(Base, UUIDPrimaryKey, Timestamps, Addressed):
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
            "seq",
            postgresql_where=text("status = 'waiting'"),
        ),
        CheckConstraint(AUDIENCE_CHECK, name="ck_practice_queue_entries_audience"),
    )

    # A queue is ordered by arrival, and `created_at` cannot express that:
    # everyone who joins in one transaction shares a `now()`, and breaking the
    # tie on a random uuid gives a stable order that is not the order they
    # arrived in. A sequence is monotonic, which is what "first come, first
    # served" actually requires.
    seq: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False, unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'waiting'"))
    matched_session_id: Mapped[uuid.UUID | None] = mapped_column()
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PracticeSession(Base, UUIDPrimaryKey, Timestamps):
    """Two people practising, one as doctor and one as patient."""

    __tablename__ = "practice_sessions"
    __table_args__ = (
        Index("ix_practice_sessions_participants", "doctor_user_id", "patient_user_id"),
        # Partial, because a session that was never recorded is the uninteresting
        # majority and the transcription job only ever asks after the rest.
        Index(
            "ix_practice_sessions_recording_state",
            "recording_state",
            postgresql_where=text("recording_state <> 'none'"),
        ),
    )

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
    peer_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("peer_sessions.id", ondelete="SET NULL", use_alter=True)
    )
    room_name: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'matched'"))
    current_phase: Mapped[str | None] = mapped_column(String(16))
    phase_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    doctor_joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    patient_joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    preparation_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_reason: Mapped[str | None] = mapped_column(String(32))
    feedback_rating: Mapped[int | None] = mapped_column(Integer)
    feedback_comment: Mapped[str | None] = mapped_column(String(2000))
    would_practice_again: Mapped[bool | None] = mapped_column(Boolean)

    # The accept handshake: a session starts `pending_accept` rather than
    # joinable, and each side records when they accepted. `accept_expires_at`
    # is when a side that never answers times the pairing out.
    doctor_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    patient_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accept_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Recording, and what it eventually becomes. Two people practising have no
    # agent in the room keeping a transcript the way an attempt's patient
    # does, so this recording is the only record there will ever be, and the
    # marking is built from it afterwards (P-1).
    egress_id: Mapped[str | None] = mapped_column(String(128))
    # The object key, not a URL: the bucket is private, so what a reader needs
    # is a presigned URL minted per read, and storing one would store something
    # that expires.
    recording_key: Mapped[str | None] = mapped_column(String(512))
    recording_state: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'none'"))
    # Why the recording or the marking did not happen, for the one person who
    # asks where their feedback is. Null while nothing has gone wrong.
    recording_error: Mapped[str | None] = mapped_column(String(200))
    # The doctor's scored attempt. `attempts.peer_session_id` points back the
    # other way; without this the session read cannot say where the feedback
    # is without scanning attempts for one that names it.
    doctor_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attempts.id", ondelete="SET NULL", use_alter=True)
    )


class PracticeHistory(Base, UUIDPrimaryKey, Timestamps):
    """What part someone last played, and how often they have practised.

    A row rather than fields on the user: it is peer-practice's own business.
    """

    __tablename__ = "practice_history"
    __table_args__ = (Index("uq_practice_history_user", "user_id", unique=True),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    last_role: Mapped[str | None] = mapped_column(String(16))
    session_count: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    # Replaces b2c's hardcoded list of three personal email addresses.
    never_doctor: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
