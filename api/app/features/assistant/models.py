"""Tables owned by `assistant`."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class AssistantSession(Base, UUIDPrimaryKey, Timestamps):
    """One conversation where the assistant helps someone use the product."""

    __tablename__ = "assistant_sessions"
    __table_args__ = (Index("ix_assistant_sessions_user", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # Rendered backend-side, exactly as an attempt's are. The worker holds no
    # templates and is handed finished text.
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    greeting: Mapped[str | None] = mapped_column(Text)
    room_name: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'active'"))
    extras: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_reason: Mapped[str | None] = mapped_column(String(64))
    usage: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class AssistantTranscriptMessage(Base, UUIDPrimaryKey):
    """Turns, kept only for help sessions.

    The other three kinds are navigation; storing them would collect recordings
    of people's screens for nothing.
    """

    __tablename__ = "assistant_transcript_messages"
    __table_args__ = (
        UniqueConstraint("session_id", "message_id", name="uq_assistant_transcript_session_message"),
        Index("ix_assistant_transcript_session_seq", "session_id", "seq"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assistant_sessions.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[str] = mapped_column(String(64), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    spoken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
