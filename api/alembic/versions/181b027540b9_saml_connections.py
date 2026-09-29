"""An organisation's SAML 2.0 identity provider (E-20).

OIDC (Clerk, Entra) left out every institution whose IdP speaks only SAML. One
connection per organisation: the IdP's entity id, sign-in URL and signing
certificate, and which attributes carry the address and name.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "181b027540b9"
down_revision: str | None = "d641a21c209a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization_saml_connections",
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("idp_entity_id", sa.String(length=500), nullable=False),
        sa.Column("idp_sso_url", sa.String(length=1000), nullable=False),
        sa.Column("idp_x509_cert", sa.Text(), nullable=False),
        sa.Column("email_attribute", sa.String(length=255), nullable=False),
        sa.Column("first_name_attribute", sa.String(length=255), nullable=True),
        sa.Column("last_name_attribute", sa.String(length=255), nullable=True),
        sa.Column("display_name_attribute", sa.String(length=255), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_organization_saml_connections_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_saml_connections")),
        sa.UniqueConstraint("org_id", name="uq_organization_saml_connections_org_id"),
    )


def downgrade() -> None:
    op.drop_table("organization_saml_connections")
