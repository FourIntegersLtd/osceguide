"""Tables owned by `tutor_memory`: what the tutor knows about one learner."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UUIDPrimaryKey
from app.features.tutor_memory.vector_column import Vector


class LearningEvent(Base, UUIDPrimaryKey):
    """One thing this person read, practised or listened to.

    Written by the browser as it happens rather than derived from anything: a
    summary opened in the app leaves no other trace, and the tutor asking "how
    did the anxiety summary go?" is the whole point of collecting them.

    `ref_id` is a string rather than a foreign key because the six kinds live
    in three slices and one of them is not a row at all; the resolver that
    turns a ref into something on screen is the frontend's.
    """

    __tablename__ = "learning_events"
    __table_args__ = (
        CheckConstraint("kind IN ('viewed', 'practised', 'listened')", name="kind"),
        CheckConstraint(
            "ref_kind IN ('summary', 'slide_deck', 'podcast', 'blog', 'station', 'management_plan')",
            name="ref_kind",
        ),
        Index("ix_learning_events_user_time", "user_id", "occurred_at"),
        # The read that answers "have they seen this lately?", which is what
        # the ten-minute dedup asks before writing another row.
        Index("ix_learning_events_dedup", "user_id", "ref_kind", "ref_id", "occurred_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # RESTRICT, not CASCADE: an exam is a catalogue entry that outlives any
    # learner, and deleting one should fail loudly rather than quietly erase
    # everybody's history of studying for it.
    exam_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exams.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    ref_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    ref_id: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class TutorNote(Base, UUIDPrimaryKey):
    """Something the tutor wrote down: how a conversation ended, or a fact told to it.

    Two kinds in one table because they are read together and forgotten
    together — "what do you know about me" is one list, and deleting it is one
    delete.
    """

    __tablename__ = "tutor_notes"
    __table_args__ = (
        CheckConstraint("kind IN ('session_summary', 'stated_fact')", name="kind"),
        Index("ix_tutor_notes_user_time", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exam_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exams.id", ondelete="RESTRICT"))
    # SET NULL rather than CASCADE: the summary is what survives the
    # conversation, and the conversation's turns are deleted on purpose once it
    # is written. A note that vanished with them would defeat the exercise.
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assistant_sessions.id", ondelete="SET NULL")
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    body: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class DebriefSummary(Base, UUIDPrimaryKey):
    """What a debrief concluded, and what was agreed to do about it.

    One per attempt, enforced by the unique constraint rather than by the job
    checking first: the queue may deliver a job twice, and two summaries of one
    debrief would have the tutor agreeing two different plans.
    """

    __tablename__ = "debrief_summaries"
    __table_args__ = (
        UniqueConstraint("attempt_id", name="uq_debrief_summaries_attempt"),
        Index("ix_debrief_summaries_user_time", "user_id", "created_at"),
    )

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exam_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exams.id", ondelete="RESTRICT"))
    key_insights: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    # `[{"text": ..., "done": false}]`. The flag is what lets the tutor ask
    # about a step by name and hear whether it happened.
    action_plan: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    narrative: Mapped[str | None] = mapped_column(Text)
    model_used: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class MaterialChunk(Base, UUIDPrimaryKey):
    """One passage of study material, and the vector it is retrieved by.

    Not owned by `stations` or `media`, though the text comes from both. This
    is a derived index rebuilt by a job, and a table that can be dropped and
    regenerated does not belong to the slice that owns the source of truth —
    it belongs to the reader that needs it, which is the tutor.

    `source_id` is a string for the same reason `learning_events.ref_id` is:
    the corpora live in different slices, and a foreign key per corpus would
    make adding a third one a schema change. The re-index deletes stale rows,
    so a deleted source's passages go on its next run rather than by cascade —
    which is the honest cost of not having the key.
    """

    __tablename__ = "material_chunks"
    __table_args__ = (
        CheckConstraint("corpus IN ('station', 'summary', 'slide_deck', 'podcast', 'blog')", name="corpus"),
        # What `upsert` writes against: one row per passage of a source, so
        # re-indexing an edited document replaces rather than duplicates.
        UniqueConstraint("corpus", "source_id", "chunk_index", name="uq_material_chunks_passage"),
        # The search filters by exam before it ranks, because a doctor may only
        # be read out of material they hold.
        Index("ix_material_chunks_exam", "exam_id", "corpus"),
        # The nearest-neighbour index. Declared here as well as in the
        # migration because `test_models_and_schema_do_not_drift` compares the
        # two: an index created only in raw SQL reads to autogenerate as one
        # the models have dropped, and the next migration would drop it.
        #
        # The operator class has to match the operator the query uses (`<=>`,
        # cosine) or the index is simply not consulted -- the query still
        # returns the right rows, by scanning every one of them.
        Index(
            "ix_material_chunks_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"lists": "100"},
        ),
    )

    corpus: Mapped[str] = mapped_column(String(24), nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    exam_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    section: Mapped[str] = mapped_column(String(40), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # Named `text` because that is what it holds. It shadows SQLAlchemy's
    # `text()` for the rest of this class body, which is why the default below
    # is `func.now()` rather than the `text("now()")` the other tables use.
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(), nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
