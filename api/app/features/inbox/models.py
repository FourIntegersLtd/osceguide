"""Tables owned by `inbox`."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey
from app.features.inbox.domain import Kind


class UserMessage(Base, UUIDPrimaryKey, Timestamps):
    """One in-app message to one person, or an announcement to everybody."""

    __tablename__ = "user_messages"
    __table_args__ = (
        CheckConstraint("kind IN ('report_answer', 'reply', 'note', 'announcement')", name="kind"),
        # An announcement has no recipient and nothing else does.
        CheckConstraint("(kind = 'announcement') = (recipient_user_id IS NULL)", name="audience"),
        Index("ix_user_messages_recipient_created", "recipient_user_id", "created_at", "id"),
        Index(
            "ix_user_messages_announcements_created",
            "created_at",
            "id",
            postgresql_where=text("recipient_user_id IS NULL"),
        ),
    )

    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    sender_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    kind: Mapped[Kind] = mapped_column(String(32), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    station_flag_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("station_flags.id", ondelete="SET NULL")
    )
    site_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("site_messages.id", ondelete="SET NULL")
    )
    # Announcements only: hidden from every inbox without losing the row.
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserMessageRead(Base):
    """That one person opened one message. Written only when they do: an announcement is
    never fanned out into a row per user."""

    __tablename__ = "user_message_reads"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_messages.id", ondelete="CASCADE"), primary_key=True
    )
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
