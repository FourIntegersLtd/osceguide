"""The outbox every slice writes into.

One table rather than one per slice: a message is a message, and a single queue
is the only way "what is stuck?" has one answer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class OutboundMessage(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "outbound_messages"
    __table_args__ = (
        # Written by the slice that needed it, so the key is that slice's
        # business. A repeat is a no-op rather than a second email.
        UniqueConstraint("idempotency_key", name="uq_outbound_messages_idempotency"),
        Index(
            "ix_outbound_messages_due",
            "available_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )

    channel: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'email'"))
    recipient: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
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
