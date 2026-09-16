"""Tables owned by `catalog`. These classes never leave this slice's repository."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class Exam(Base, UUIDPrimaryKey, Timestamps):
    """A published assessment framework. Four rows, seeded, the same for everyone.

    Replaces b2c's `app_type` string and the 4x20 COLLECTION_MAPPING it indexed.
    A fifth exam is a row here, not another twenty collection names.
    """

    __tablename__ = "exams"

    code: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    framework_id: Mapped[str] = mapped_column(String(64), nullable=False)
    feedback_model_key: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default=text("'default'")
    )
    default_reading_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    default_simulation_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    station_attempt_limit: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))


class Programme(Base, UUIDPrimaryKey, Timestamps):
    """One organisation offering one exam. This is what `b2b_exams` rows were."""

    __tablename__ = "org_programmes"
    __table_args__ = (UniqueConstraint("org_id", "exam_id", name="uq_org_programmes_org_exam"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'draft'"))
    source: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'custom'"))
    import_ref: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
