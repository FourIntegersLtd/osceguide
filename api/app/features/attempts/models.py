"""Tables owned by `attempts`. These classes never leave this slice's repository."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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

from app.core.db import Base, Timestamps, UUIDPrimaryKey

# Exactly one optional reference must match the kind. Written as a CHECK rather
# than left to the service, because six code paths create attempts and only one
# of them needs to be wrong for a slot to end up with two live attempts.
_NO_REFERENCES = (
    "slot_id IS NULL AND set_entry_id IS NULL AND peer_session_id IS NULL AND source_attempt_id IS NULL"
)

_KIND_REFERENCE_CHECK = " OR ".join(
    (
        f"(kind = 'practice' AND {_NO_REFERENCES})",
        f"(kind = 'self_practice' AND {_NO_REFERENCES})",
        "(kind = 'set_station' AND set_entry_id IS NOT NULL AND slot_id IS NULL AND peer_session_id IS NULL)",
        "(kind = 'debrief' AND source_attempt_id IS NOT NULL)",
        "(kind = 'exam_slot' AND slot_id IS NOT NULL AND set_entry_id IS NULL AND peer_session_id IS NULL)",
        "(kind = 'peer' AND peer_session_id IS NOT NULL AND slot_id IS NULL AND set_entry_id IS NULL)",
    )
)


class Attempt(Base, UUIDPrimaryKey, Timestamps):
    """One candidate running one scenario.

    `id` is its own identity. b2c made the attempt id the room name and b2b made
    it the slot id; both leaked an implementation detail into the worker
    contract, and b2b's meant re-dispatching a slot overwrote the first
    recording.
    """

    __tablename__ = "attempts"
    __table_args__ = (
        CheckConstraint(_KIND_REFERENCE_CHECK, name="ck_attempts_kind_matches_reference"),
        Index("ix_attempts_user_created", "user_id", "created_at"),
        Index("ix_attempts_org_created", "org_id", "created_at"),
        Index("ix_attempts_station_version", "station_version_id"),
        # A slot has at most one attempt that has not failed; a re-dispatch
        # fails the old one first and then creates a new row.
        Index(
            "uq_attempts_live_slot",
            "slot_id",
            unique=True,
            postgresql_where=text("slot_id IS NOT NULL AND status <> 'failed'"),
        ),
    )

    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False)
    station_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("station_versions.id", ondelete="RESTRICT")
    )

    slot_id: Mapped[uuid.UUID | None] = mapped_column()
    set_entry_id: Mapped[uuid.UUID | None] = mapped_column()
    peer_session_id: Mapped[uuid.UUID | None] = mapped_column()
    source_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attempts.id", ondelete="SET NULL")
    )

    # The frozen AssessmentDefinition, written once on the first successful
    # render. Justified JSON: it is the engine's own document, validated by the
    # engine, and storing it relationally would mean re-deriving it to replay.
    definition: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    definition_frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    room_name: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'created'"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_reason: Mapped[str | None] = mapped_column(String(200))


class TranscriptMessage(Base, UUIDPrimaryKey):
    """One turn. No updated_at: a spoken turn is never edited."""

    __tablename__ = "transcript_messages"
    __table_args__ = (
        # Chunk posts repeat, because the worker sends them best-effort and
        # never reads the response.
        UniqueConstraint("attempt_id", "message_id", name="uq_transcript_messages_attempt_message"),
        Index("ix_transcript_messages_attempt_seq", "attempt_id", "seq"),
    )

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[str] = mapped_column(String(64), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    spoken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class Transcript(Base, UUIDPrimaryKey, Timestamps):
    """The delivery record for an attempt's turns."""

    __tablename__ = "transcripts"
    __table_args__ = (UniqueConstraint("attempt_id", name="uq_transcripts_attempt"),)

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False
    )
    complete: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    runtime_label: Mapped[str | None] = mapped_column(String(64))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssessmentResult(Base, UUIDPrimaryKey, Timestamps):
    """What the engine scored, kept immutably.

    Unique on (attempt, policy_version): re-running the same policy stores
    nothing new, and scoring under a different one sits beside the old result
    rather than replacing it.
    """

    __tablename__ = "assessment_results"
    __table_args__ = (
        UniqueConstraint("attempt_id", "policy_version", name="uq_assessment_results_attempt_policy"),
    )

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False
    )
    framework_id: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(128), nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(64))
    # The engine's own output, already validated against its JSON Schema.
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
