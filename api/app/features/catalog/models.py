"""Tables owned by `catalog`. These classes never leave this slice's repository."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey

_OWNER_MATCHES_ORG = (
    "(owner_kind = 'platform' AND org_id IS NULL) OR (owner_kind = 'org' AND org_id IS NOT NULL)"
)


class Exam(Base, UUIDPrimaryKey, Timestamps):
    """An assessment framework, written by the platform or by an institution.

    `owner_kind` is the same split stations and rubrics carry, and keeps the
    two arms independent. A **platform** exam is the consumer catalogue,
    published by us and visible to everyone. An **org** exam is an
    institution's own, published on its own schedule and never shown in the
    consumer catalogue.

    `framework_id` is gone: what an exam is marked against is a rubric
    version, and that version's id is the framework id everything downstream
    records.
    """

    __tablename__ = "exams"
    __table_args__ = (
        CheckConstraint(
            "status <> 'published' OR rubric_version_id IS NOT NULL",
            name="ck_exams_published_has_rubric",
        ),
        CheckConstraint(_OWNER_MATCHES_ORG, name="ck_exams_owner_matches_org"),
        # A code is unique within its owner, not globally. Ashford may call its
        # own exam `plab` while the platform publishes a `plab` of its own;
        # forcing one namespace would let whoever registered a code first
        # reserve it for every institution on the platform.
        Index(
            "uq_exams_platform_code",
            "code",
            unique=True,
            postgresql_where=text("org_id IS NULL"),
        ),
        Index(
            "uq_exams_org_code",
            "org_id",
            "code",
            unique=True,
            postgresql_where=text("org_id IS NOT NULL"),
        ),
    )

    owner_kind: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'platform'"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(CITEXT, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'draft'"))
    # What this exam is marked against. A published version its own owner may
    # use: the platform's exams name platform rubrics, an institution's may
    # name its own rubric or a platform one it has been given to read.
    rubric_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rubric_versions.id", ondelete="RESTRICT")
    )
    default_reading_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    default_simulation_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    station_attempt_limit: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))
    # Whether partner attribution links may name this exam. Consumer-side, so
    # it is only ever set on a platform exam.
    partner_pilot: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    # How this exam differs from the others apart from its rubric: labels,
    # which debrief modes and help it offers, which generation prompts it
    # uses. Validated by `schemas.ExamSettings`, whose defaults make `{}` a
    # whole exam. Justified JSON: a bag of per-exam presentation choices that
    # grows with the product and is never queried by field.
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )


class Programme(Base, UUIDPrimaryKey, Timestamps):
    """One organisation offering one exam.

    The exam it names is either the institution's own or one the platform has
    published; a programme carries no content, it is the label a year's
    sittings are grouped under.
    """

    __tablename__ = "org_programmes"
    __table_args__ = (UniqueConstraint("org_id", "exam_id", name="uq_org_programmes_org_exam"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'draft'"))
    source: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'custom'"))
    import_ref: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
