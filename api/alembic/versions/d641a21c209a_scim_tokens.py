"""Bearer tokens for an organisation's SCIM provisioning connector (E-21).

An identity provider (Entra, Okta) provisions an institution's roster over
SCIM 2.0 with a per-organisation bearer token. Only its sha256 is stored.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "d641a21c209a"
down_revision: str | None = "3d7c790f920b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scim_tokens",
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_prefix", sa.String(length=16), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_scim_tokens_created_by_users"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_scim_tokens_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scim_tokens")),
        sa.UniqueConstraint("token_hash", name="uq_scim_tokens_token_hash"),
    )
    op.create_index("ix_scim_tokens_org", "scim_tokens", ["org_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_scim_tokens_org", table_name="scim_tokens")
    op.drop_table("scim_tokens")
