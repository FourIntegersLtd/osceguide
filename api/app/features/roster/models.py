"""Tables owned by `roster`. These classes never leave this slice's repository."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class Cohort(Base, UUIDPrimaryKey, Timestamps):
    """An intake: the year group a trainee belongs to."""

    __tablename__ = "cohorts"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_cohorts_org_name"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    academic_year: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class Trainee(Base, UUIDPrimaryKey, Timestamps):
    """Someone an organisation teaches.

    Separate from `users` because an institution rosters people before they have
    ever signed in — `user_id` is filled when they do.
    """

    __tablename__ = "trainees"
    __table_args__ = (
        UniqueConstraint("org_id", "email", name="uq_trainees_org_email"),
        Index("ix_trainees_org_cohort", "org_id", "cohort_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    cohort_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cohorts.id", ondelete="SET NULL"))
    access_revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # GDPR erasure for a row a plain `DELETE` refuses (`trainee_in_use`) —
    # a real decision exists and stays; the address and name naming the
    # person do not. Written once, never cleared: see `service_edit.anonymise_trainee`.
    anonymised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TraineeGroup(Base, UUIDPrimaryKey, Timestamps):

    __tablename__ = "trainee_groups"
    __table_args__ = (UniqueConstraint("org_id", "label_normalized", name="uq_trainee_groups_org_label"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    # Stored so the uniqueness constraint means what people expect: "Cohort A"
    # and "cohort a" are one group.
    label_normalized: Mapped[str] = mapped_column(String(200), nullable=False)


class TraineeGroupMember(Base, UUIDPrimaryKey, Timestamps):
    """A trainee's membership in a group. See `domain` for why this is a real table."""

    __tablename__ = "trainee_group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "trainee_id", name="uq_trainee_group_members_group_trainee"),
        Index("ix_trainee_group_members_trainee", "trainee_id"),
    )

    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trainee_groups.id", ondelete="CASCADE"), nullable=False
    )
    trainee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trainees.id", ondelete="CASCADE"), nullable=False
    )
