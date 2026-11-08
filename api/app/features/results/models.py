"""Tables owned by `results`.

Revisions and events are **append-only, enforced by a trigger** rather than by
convention: a candidate's outcome has to be defensible months later, so the
database refuses to let it be edited at all.
"""

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


class CandidateResultRevision(Base, UUIDPrimaryKey):
    """One version of a decision. Never updated; a change is a new revision."""

    __tablename__ = "candidate_result_revisions"
    __table_args__ = (
        UniqueConstraint("sitting_id", "trainee_id", "revision", name="uq_candidate_result_revisions_chain"),
        CheckConstraint("revision > 0", name="ck_candidate_result_revisions_positive"),
        CheckConstraint(
            "workflow_state IN ('draft', 'signed_off', 'released')",
            name="ck_candidate_result_revisions_workflow",
        ),
        # A signed-off revision names its signer; a released one names its
        # releaser. Enforced here so an incomplete record cannot be written.
        CheckConstraint(
            "workflow_state <> 'signed_off' OR signed_off_by IS NOT NULL",
            name="ck_candidate_result_revisions_signer",
        ),
        CheckConstraint(
            "workflow_state <> 'released' OR released_by IS NOT NULL",
            name="ck_candidate_result_revisions_releaser",
        ),
        Index("ix_candidate_result_revisions_lookup", "org_id", "sitting_id", "trainee_id"),
        Index(
            "ix_candidate_result_revisions_org_released",
            "org_id",
            "sitting_id",
            postgresql_where=text("released_at IS NOT NULL"),
            postgresql_concurrently=True,
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    sitting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sittings.id", ondelete="CASCADE"), nullable=False
    )
    # `RESTRICT`, not `CASCADE`: a decision revision is the defensible record a
    # candidate's result actually is. Roster's `delete_trainee` depends on this,
    # refusing with `trainee_in_use` for this table rather than cascading
    # through a candidate's decision history.
    trainee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trainees.id", ondelete="RESTRICT"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    supersedes_revision: Mapped[int | None] = mapped_column(Integer)
    workflow_state: Mapped[str] = mapped_column(String(16), nullable=False)
    assessment_outcome: Mapped[str | None] = mapped_column(String(16))
    recruitment_outcome: Mapped[str | None] = mapped_column(String(16))
    rationale: Mapped[str | None] = mapped_column(Text)
    moderation_notes: Mapped[str | None] = mapped_column(Text)
    # What the decision was made against, and its hash, so a result signed off
    # against one set of scores is not released after those scores move.
    evidence_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    evidence_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    disclosure: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    signed_off_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    signed_off_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class CandidateResultEvent(Base, UUIDPrimaryKey):
    """What happened to a decision, append-only."""

    __tablename__ = "candidate_result_events"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_candidate_result_events_idempotency"),
        Index("ix_candidate_result_events_revision", "revision_id"),
    )

    revision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_result_revisions.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class CandidateResultNotification(Base, UUIDPrimaryKey, Timestamps):
    """Outbox for telling a candidate.

    A row rather than an email sent inline, so a release is not lost because a
    mail provider was briefly down.
    """

    __tablename__ = "candidate_result_notifications"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_candidate_result_notifications_idempotency"),
        Index(
            "ix_candidate_result_notifications_pending",
            "available_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_result_events.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'email'"))
    recipient: Mapped[str] = mapped_column(String(320), nullable=False)
    template_key: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'pending'"))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class ResultAppeal(Base, UUIDPrimaryKey, Timestamps):
    """A request to look again at a released result.

    The row is the workflow (open, in review, resolved, declined); the result it leads to is a new
    revision on `candidate_result_revisions`, never an edit of the one appealed. `reason` and
    `decision_note` are personal text and become `[erased]` when the candidate's data is deleted.
    """

    __tablename__ = "result_appeals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'in_review', 'resolved', 'declined')", name="ck_result_appeals_status"
        ),
        CheckConstraint(
            "status <> 'in_review' OR assigned_to IS NOT NULL", name="ck_result_appeals_assigned"
        ),
        # One appeal at a time per candidate and sitting: a second request while one is live is a mistake.
        Index(
            "uq_result_appeals_active",
            "sitting_id",
            "trainee_id",
            unique=True,
            postgresql_where=text("status IN ('open', 'in_review')"),
        ),
        Index("ix_result_appeals_org_status", "org_id", "status"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    sitting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sittings.id", ondelete="CASCADE"), nullable=False
    )
    trainee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trainees.id", ondelete="RESTRICT"), nullable=False
    )
    # The released revision being questioned, and the one the outcome appended (null until resolved).
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome_revision: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'open'"))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    on_behalf: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_note: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
