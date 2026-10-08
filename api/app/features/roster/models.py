"""Tables owned by `roster`. These classes never leave this slice's repository."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Revisioned, Timestamps, UUIDPrimaryKey


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


class Trainee(Base, UUIDPrimaryKey, Timestamps, Revisioned):
    """Someone an organisation teaches.

    Separate from `users` because an institution rosters people before they have
    ever signed in — `user_id` is filled when they do.
    """

    __tablename__ = "trainees"
    __table_args__ = (
        UniqueConstraint("org_id", "email", name="uq_trainees_org_email"),
        Index("ix_trainees_org_cohort", "org_id", "cohort_id"),
        # Backs `access_revoked=` on the roster list.
        Index("ix_trainees_org_access_revoked", "org_id", "access_revoked_at"),
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
    """A named group of trainees at an organisation, e.g. a teaching set."""

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


class ScimToken(Base, UUIDPrimaryKey, Timestamps):
    """A bearer token an organisation's identity provider uses to provision its roster (E-21).

    Only a hash is stored: the token is shown once, when it is issued, and a
    database dump must not hand anybody the ability to add people to an
    institution. Revoked rather than deleted, so "which connector did this"
    stays answerable.
    """

    __tablename__ = "scim_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_scim_tokens_token_hash"),
        Index("ix_scim_tokens_org", "org_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    # sha256 of the token, hex. The token itself has 256 bits of entropy, so an
    # unsalted fast hash is enough: there is nothing to guess.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # The first characters, so an admin can tell two tokens apart on screen.
    token_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
