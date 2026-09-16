"""Tables owned by `marketplace`."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class AvailabilityPost(Base, UUIDPrimaryKey, Timestamps):
    """A time someone is free to practise with a peer."""

    __tablename__ = "availability_posts"
    __table_args__ = (
        Index("ix_availability_posts_open", "starts_at", postgresql_where=text("status = 'available'")),
        Index("ix_availability_posts_owner", "owner_user_id"),
    )

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("30"))
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'available'"))
    claimed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PeerSession(Base, UUIDPrimaryKey, Timestamps):
    """The session a claim creates. Two people, one room, one appointed time."""

    __tablename__ = "peer_sessions"
    __table_args__ = (Index("ix_peer_sessions_participants", "owner_user_id", "claimer_user_id"),)

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
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'scheduled'"))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
