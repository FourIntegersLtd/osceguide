"""Tables owned by `catalog`. These classes never leave this slice's repository."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class Exam(Base, UUIDPrimaryKey, Timestamps):
    """An assessment framework a platform admin published.

    Replaces b2c's `app_type` string and the 4x20 COLLECTION_MAPPING it indexed.
    The table used to be seeded with four rows mirrored by a Python tuple, so a
    fifth exam meant a migration, a code change and a release. It is now empty
    until somebody writes one.

    `framework_id` is gone: what an exam is marked against is a rubric version,
    and that version's id is the framework id everything downstream records.
    """

    __tablename__ = "exams"
    __table_args__ = (
        CheckConstraint(
            "status <> 'published' OR rubric_version_id IS NOT NULL",
            name="ck_exams_published_has_rubric",
        ),
    )

    code: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'draft'"))
    # What this exam is marked against. A published, platform-owned version:
    # an exam belongs to everyone, so it cannot be bound to one org's rubric.
    rubric_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rubric_versions.id", ondelete="RESTRICT")
    )
    default_reading_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    default_simulation_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    station_attempt_limit: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))
    # Whether partner attribution links may name this exam. Was `PILOT_EXAMS`,
    # a tuple of three codes in the growth slice.
    partner_pilot: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))


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
