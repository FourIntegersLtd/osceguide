"""Tables owned by `marketplace`."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import AUDIENCE_CHECK, Addressed, Base, Timestamps, UUIDPrimaryKey


class AvailabilityPost(Base, UUIDPrimaryKey, Timestamps, Addressed):
    """A time someone is free to practise with a peer."""

    __tablename__ = "availability_posts"
    __table_args__ = (
        Index("ix_availability_posts_open", "starts_at", postgresql_where=text("status = 'available'")),
        Index("ix_availability_posts_owner", "owner_user_id"),
        CheckConstraint(AUDIENCE_CHECK, name="ck_availability_posts_audience"),
        Index("ix_availability_posts_audience_org_id", "audience_org_id", "starts_at"),
        Index("ix_availability_posts_audience_group_id", "audience_group_id", "starts_at"),
        # Backs `/marketplace/slots?status=&when=`, which also matches claimed
        # (not just open) posts.
        Index("ix_availability_posts_status_starts_at", "status", "starts_at"),
    )

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("30"))
    note: Mapped[str | None] = mapped_column(Text)
    # available -> claimed. Either becomes cancelled if the person who offered it takes it back.
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'available'"))
    claimed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PeerSession(Base, UUIDPrimaryKey, Timestamps):
    """The session a claim creates. Two people, one room, one appointed time."""

    __tablename__ = "peer_sessions"
    __table_args__ = (
        Index("ix_peer_sessions_participants", "owner_user_id", "claimer_user_id"),
        Index("ix_peer_sessions_claimer_user_id", "claimer_user_id"),
        # Backs `/me/peer-sessions?when=`.
        Index("ix_peer_sessions_status_starts_at", "status", "starts_at"),
    )

    post_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("availability_posts.id", ondelete="SET NULL")
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    claimer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    room_name: Mapped[str | None] = mapped_column(String(200))
    # The next three are filled in when the first person joins: the live practice
    # session both people use, and who plays which part in it.
    practice_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="SET NULL")
    )
    doctor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    patient_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # scheduled -> active once someone joins; cancelled from either.
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'scheduled'"))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Set by `jobs.send_marketplace_session_reminders` once it has queued the
    # "starts in an hour" email to both participants. Null until then, and the
    # job's own idempotency check: claimed with an atomic
    # `UPDATE ... WHERE reminder_sent_at IS NULL`, so two workers polling at
    # once never both queue the reminder for the same session.
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
