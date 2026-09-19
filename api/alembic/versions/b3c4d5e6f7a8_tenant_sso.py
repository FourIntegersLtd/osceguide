"""Move the partner sign-in list out of the browser bundle.

Which organisation a visitor belongs to — before they have typed anything — was
answered in the retiring client by a constant:

    const PARTNER_SSO_HOSTS = ["bmj.osceguide.com"];

with the tenant slug, the button's wording and the "no password form here" rule
compiled in beside it. Adding a partner meant a frontend deploy, and the four
facts could drift apart from each other and from the backend.

`organization_sso` holds the arrangement and `organization_sso_bindings` holds
the hosts and email domains that resolve to it. The binding is unique across
the whole platform rather than within an organisation: a hostname belongs to
exactly one, and two rows claiming `nhs.net` would make home-realm discovery a
coin toss.

Nothing here verifies an identity. Who does that is still an open decision —
the retiring backend brokered through Clerk to Microsoft — so `provider` names
what a row expects and no row implies a flow exists.

Revision ID: b3c4d5e6f7a8
Revises: 7c1e9f40ab52
Create Date: 2026-09-19 00:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b3c4d5e6f7a8"
down_revision: str | None = "7c1e9f40ab52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization_sso",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("issuer", sa.String(length=255), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sso_only", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sign_in_label", sa.String(length=80), nullable=True),
        sa.Column("default_exam_code", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.id"], name="fk_organization_sso_org_id_organizations", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("org_id", name="uq_organization_sso_org_id"),
    )

    # Restricting sign-in to SSO while SSO is off would leave nobody a way in.
    # The service refuses it; the table refuses it too, because a settings row
    # is exactly the kind of thing that gets edited by hand at three in the
    # morning.
    op.create_check_constraint(
        "ck_organization_sso_only_requires_enabled",
        "organization_sso",
        "NOT sso_only OR enabled",
    )

    op.create_table(
        "organization_sso_bindings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sso_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("value", postgresql.CITEXT(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sso_id"],
            ["organization_sso.id"],
            name="fk_organization_sso_bindings_sso_id_organization_sso",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("kind", "value", name="uq_organization_sso_bindings_kind_value"),
    )
    op.create_check_constraint(
        "ck_organization_sso_bindings_kind",
        "organization_sso_bindings",
        "kind IN ('host', 'email_domain')",
    )
    op.create_index(
        "ix_organization_sso_bindings_sso_id", "organization_sso_bindings", ["sso_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_organization_sso_bindings_sso_id", table_name="organization_sso_bindings")
    op.drop_table("organization_sso_bindings")
    op.drop_table("organization_sso")
