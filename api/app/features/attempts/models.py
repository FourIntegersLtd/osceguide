"""Tables owned by `attempts`. These classes never leave this slice's repository."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
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
        # The status vocabulary, in the database rather than only in
        # `domain.Status`. `set_status` took a bare string, so a typo wrote a
        # status nothing would ever match and the attempt stalled in it.
        CheckConstraint(
            "status IN ('created', 'running', 'interaction_complete', 'evaluated', 'failed')",
            name="ck_attempts_status",
        ),
        Index("ix_attempts_user_created", "user_id", "created_at"),
        Index("ix_attempts_org_created", "org_id", "created_at"),
        # Backs `/me/attempts?search=`, which matches the exam's code via
        # ids resolved from `catalog.exam_ids_matching_code`.
        Index("ix_attempts_exam_id", "exam_id"),
        Index("ix_attempts_station_version", "station_version_id"),
        # A slot has at most one attempt that has not failed; a re-dispatch
        # fails the old one first and then creates a new row.
        Index(
            "uq_attempts_live_slot",
            "slot_id",
            unique=True,
            postgresql_where=text("slot_id IS NOT NULL AND status <> 'failed'"),
        ),
        # An imported attempt is identified by where it came from, so a second
        # import run updates nothing rather than duplicating history. Partial,
        # because every attempt created since the cutover has no legacy id.
        Index(
            "uq_attempts_legacy_ref",
            "legacy_ref",
            unique=True,
            postgresql_where=text("legacy_ref IS NOT NULL"),
        ),
        Index(
            "ix_attempts_set_entry_id",
            "set_entry_id",
            postgresql_where=text("set_entry_id IS NOT NULL"),
            postgresql_concurrently=True,
        ),
        Index(
            "ix_attempts_peer_session_id",
            "peer_session_id",
            postgresql_where=text("peer_session_id IS NOT NULL"),
            postgresql_concurrently=True,
        ),
        Index(
            "ix_attempts_source_attempt_id",
            "source_attempt_id",
            postgresql_where=text("source_attempt_id IS NOT NULL"),
            postgresql_concurrently=True,
        ),
        # One unstarted practice start per person and station: a double click or retry makes one row.
        Index(
            "uq_attempts_one_unstarted",
            "user_id",
            "kind",
            "exam_id",
            "org_id",
            "station_version_id",
            "set_entry_id",
            unique=True,
            postgresql_where=text(
                "status = 'created' AND started_at IS NULL AND definition_frozen_at IS NULL "
                "AND room_name IS NULL AND station_version_id IS NOT NULL "
                "AND kind IN ('practice', 'set_station', 'self_practice')"
            ),
            postgresql_nulls_not_distinct=True,
            postgresql_concurrently=True,
        ),
    )

    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False)
    station_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("station_versions.id", ondelete="RESTRICT")
    )

    # Real foreign keys, and `RESTRICT` rather than `CASCADE` or `SET NULL`:
    # an attempt is a recording of something that happened to a person, and
    # deleting the slot it belonged to must not quietly take the transcript
    # with it. `SET NULL` is not available either — the CHECK above requires
    # an `exam_slot` attempt to name its slot.
    slot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("slots.id", ondelete="RESTRICT"))
    # `feedback_template_version_id` (a binding to the now-removed
    # `feedback_template_versions` table) was dropped 2026-09-24: the
    # parameter it was written from was never called with a real value
    # anywhere in the codebase, and nothing ever read the column back. See
    # `rubrics/models.py` for the removal of the table it pointed at.
    set_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("station_set_entries.id", ondelete="RESTRICT")
    )
    peer_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="RESTRICT")
    )
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
    # When retention or a staff deletion removed the transcript; the attempt and its mark stay.
    content_erased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_reason: Mapped[str | None] = mapped_column(String(200))
    # Where this row came from in Firestore or b2b, e.g.
    # `b2c:transcript:abc123`. Null for everything created since the cutover.
    # Dropped with the `migration` package once every tenant is across.
    legacy_ref: Mapped[str | None] = mapped_column(String(200))


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
    # A finished attempt's turns as one document ({"v": 1, "turns": [...]}), replacing its
    # transcript_messages rows. Deferred so a page read never detoasts it; the count is plain.
    # "Compacted" means `message_count IS NOT NULL`: compaction writes both columns in one
    # statement, never for an attempt with no rows, so the count is always positive when set.
    messages: Mapped[dict[str, Any] | None] = mapped_column(JSONB, deferred=True)
    message_count: Mapped[int | None] = mapped_column(Integer)


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


# --- Coverage is provisional evidence, never an assessment result.


class AttemptLiveCoverage(Base):
    """The competencies a practice attempt's consultation has touched so far.

    Provisional evidence for the live panel, not a stored result: it is overwritten as the
    conversation goes on and carries no weight once the attempt is actually marked.
    """

    __tablename__ = "attempt_live_coverage"

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


# --- Non-verbal feedback: numbers measured in the candidate's browser, never video.


class NonverbalConsent(Base):
    """One person's consent to camera-based non-verbal feedback, and when they withdrew it."""

    __tablename__ = "nonverbal_consents"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AttemptNonverbalBatch(Base):
    """Up to 30 one-second samples posted by the browser; deleted once the summary is written."""

    __tablename__ = "attempt_nonverbal_batches"

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), primary_key=True
    )
    seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Server clock minus the browser's clock when the batch was sent, to line samples up with turns.
    skew_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    samples: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AttemptNonverbalSummary(Base):
    """The facts and the written non-verbal section for one attempt. Never part of a mark."""

    __tablename__ = "attempt_nonverbal_summaries"

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), primary_key=True
    )
    # ready | insufficient | failed
    state: Mapped[str] = mapped_column(Text, nullable=False)
    facts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    feedback: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    model_used: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
