"""Let the platform author a station template, and drop the table nothing used.

`station_templates` and its versions were `org_id NOT NULL`, so a station shape
could only ever belong to an institution — the platform's own library stations
had no template at all and were rendered by a formatter that branched on the
exam's code. They get the same `owner_kind` `stations` already had.

`station_schemas` goes. It was a second document-shaped table for the same idea
— "what a station of this kind contains" — with no repository, no service, no
route and no reader anywhere in the app or the tests. Block definitions live in
a template version's `structure`.

Revision ID: c9d0e1f2a3b4
Revises: d0e1f2a3b4c5
Create Date: 2026-09-17 16:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c9d0e1f2a3b4"
down_revision: str | None = "d0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OWNER_MATCHES_ORG = (
    "(owner_kind = 'platform' AND org_id IS NULL) OR (owner_kind = 'org' AND org_id IS NOT NULL)"
)

TABLES = ("station_templates", "station_template_versions")


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column("owner_kind", sa.String(length=16), server_default=sa.text("'org'"), nullable=False),
        )
        op.alter_column(table, "org_id", existing_type=sa.Uuid(), nullable=True)
        op.create_check_constraint(f"ck_{table}_owner_matches_org", table, OWNER_MATCHES_ORG)
        # The default existed only to fill the rows that were already there.
        op.alter_column(table, "owner_kind", server_default=None)

    op.drop_table("station_schemas")


def downgrade() -> None:
    op.create_table(
        "station_schemas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("structure", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.id"], name="fk_station_schemas_org_id_organizations", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_station_schemas"),
        sa.UniqueConstraint("org_id", "name", name="uq_station_schemas_org_name"),
    )
    for table in TABLES:
        op.drop_constraint(f"ck_{table}_owner_matches_org", table, type_="check")
        op.execute(f"DELETE FROM {table} WHERE org_id IS NULL")
        op.alter_column(table, "org_id", existing_type=sa.Uuid(), nullable=False)
        op.drop_column(table, "owner_kind")
