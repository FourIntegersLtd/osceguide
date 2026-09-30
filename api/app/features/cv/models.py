"""Tables owned by `cv`."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class Cv(Base, UUIDPrimaryKey, Timestamps):
    """One uploaded CV, and what was read out of it.

    The PDF itself is not kept: its text is pulled on upload and the structured result is what the
    product shows, so storing the bytes would store nothing anybody reads. `status` moves one way,
    `processing` → `completed` or `failed`; the row is written before the model is called so a person
    who closes the tab still comes back to a result rather than to nothing.
    """

    __tablename__ = "cvs"
    __table_args__ = (Index("ix_cvs_user_id", "user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # `processing`, `completed` or `failed`. A string rather than an enum the
    # database knows: the only reader is this slice, and the value travels to
    # the client, which switches on it.
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'processing'"))

    # What the person called the file. Kept for the list, never re-opened.
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False, server_default=text("''"))

    # The text pulled from the PDF on upload, so the background job that
    # structures it needs neither the file nor a second parse.
    extracted_text: Mapped[str | None] = mapped_column(Text)

    # The sections the model read it into, as `schemas.StructuredCv`. Null
    # until the job completes.
    structured: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Why it failed, for the person to read. Null unless `status` is `failed`.
    error: Mapped[str | None] = mapped_column(Text)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
