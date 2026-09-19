"""Tables owned by `sso`.

Two, and the split is the point. `organization_sso` is what an organisation's
sign-in looks like; `organization_sso_bindings` is how a visitor is recognised
as belonging to it before they have typed a password or proved anything.

Bindings are their own rows because they are the thing looked up — by `Host:`
header, or by the domain of a typed address — and because a hostname must
belong to exactly one organisation. A JSON array on the parent could not say
that, and two partners claiming one host is not a conflict anybody wants to
discover from a support ticket.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class OrganizationSso(Base, UUIDPrimaryKey, Timestamps):
    """One organisation's sign-in arrangement. At most one per organisation."""

    __tablename__ = "organization_sso"
    __table_args__ = (UniqueConstraint("org_id", name="uq_organization_sso_org_id"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )

    # Who will vouch for the identity. Stored before anything verifies one, so
    # a row says what it expects rather than implying whatever exists today.
    provider: Mapped[str] = mapped_column(String(32), nullable=False)

    # The broker's own identity — a Clerk frontend domain, or an Entra issuer.
    # Not a secret: it is half of what a discovery document is fetched from.
    issuer: Mapped[str | None] = mapped_column(String(255))

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Whether the password form is refused for the people this recognises.
    # The dangerous flag, which is why the domain refuses it without `enabled`.
    sso_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # What the button says. Null takes the provider's default rather than
    # rendering a button with no words on it.
    sign_in_label: Mapped[str | None] = mapped_column(String(80))

    # Which exam a white-label site lands on. The retiring tenant record called
    # this `defaultExam` and the sign-in page read it to pick a dashboard.
    default_exam_code: Mapped[str | None] = mapped_column(String(32))


class OrganizationSsoBinding(Base, UUIDPrimaryKey, Timestamps):
    """A host, or an email domain, that means one organisation.

    `value` is case-insensitive because hostnames and email domains both are,
    and because the alternative is a lookup that misses when somebody's browser
    sends `BMJ.osceguide.com`.
    """

    __tablename__ = "organization_sso_bindings"
    __table_args__ = (
        # Unique across every organisation, not within one: a hostname belongs
        # to exactly one, and so does an email domain. Two rows claiming
        # `nhs.net` would make home-realm discovery a coin toss.
        UniqueConstraint("kind", "value", name="uq_organization_sso_bindings_kind_value"),
        # Reading an organisation's own bindings back for the admin screen.
        Index("ix_organization_sso_bindings_sso_id", "sso_id"),
    )

    sso_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization_sso.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    value: Mapped[str] = mapped_column(CITEXT, nullable=False)
