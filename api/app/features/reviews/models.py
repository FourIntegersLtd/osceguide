"""Tables owned by `reviews`.

b2b keeps all three of these in one wide table discriminated by a
`feedback_kind` column, with **no foreign keys at all**. Three tables, each with
real keys, because they have different owners, different lifecycles and
different uniqueness.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class SlotReview(Base, UUIDPrimaryKey, Timestamps):
    """A rubric filled in against one slot, by staff or by a peer observer."""

    __tablename__ = "slot_reviews"
    __table_args__ = (
        # One review per person per slot: submitting twice edits the first.
        UniqueConstraint("slot_id", "submitted_by", name="uq_slot_reviews_slot_submitter"),
        Index("ix_slot_reviews_org", "org_id"),
    )

    slot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("slots.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    submitted_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Set when a trainee reviews a peer rather than staff reviewing them.
    observer_trainee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trainees.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'draft'"))
    # A selection over the bound feedback template, whose shape the org defines.
    field_values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GpLeadReview(Base, UUIDPrimaryKey, Timestamps):
    """A revisioned second opinion on a slot.

    One per slot, edited in place, with a revision counter because two reviewers
    can hold the same screen open.
    """

    __tablename__ = "gp_lead_reviews"
    __table_args__ = (UniqueConstraint("slot_id", name="uq_gp_lead_reviews_slot"),)

    slot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("slots.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'draft'"))
    overall_rag: Mapped[str | None] = mapped_column(String(1))
    field_values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CircuitReview(Base, UUIDPrimaryKey, Timestamps):
    """What a supervisor finalises for a whole circuit."""

    __tablename__ = "circuit_reviews"
    __table_args__ = (UniqueConstraint("circuit_id", name="uq_circuit_reviews_circuit"),)

    circuit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("circuits.id", ondelete="CASCADE"), nullable=False
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    merged_notes: Mapped[str | None] = mapped_column(Text)
    contributions: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finalized_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
