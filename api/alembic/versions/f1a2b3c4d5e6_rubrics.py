"""Let a rubric be written rather than shipped.

What a candidate is marked against lived in the engine package: a Python
constant naming the domains and competencies, a hand-written JSON Schema whose
`description` strings were the only place the marking descriptors existed, and
one of three `.txt` prompts chosen by a dict keyed on framework id. Nobody
could add an exam, or correct a descriptor, without a release of the engine.

Two tables replace all of that. `owner_kind` is the same shape `stations`
already uses, so the platform's rubrics and an institution's are the same thing
with a different owner rather than two systems.

There is deliberately no `exam_id`: an exam names the rubric version it is
marked with, never the other way round, which is what lets an institution
author a rubric without inventing an exam to hang it on.

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-09-17 14:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OWNER_MATCHES_ORG = (
    "(owner_kind = 'platform' AND org_id IS NULL) OR (owner_kind = 'org' AND org_id IS NOT NULL)"
)

TOUCHED_TABLES = ("rubrics", "rubric_versions")


def upgrade() -> None:
    op.create_table(
        "rubrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_kind", sa.String(length=16), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], name="fk_rubrics_org_id_organizations", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_rubrics"),
        sa.CheckConstraint(OWNER_MATCHES_ORG, name="ck_rubrics_owner_matches_org"),
    )
    op.create_index("ix_rubrics_org", "rubrics", ["org_id"], unique=False)

    op.create_table(
        "rubric_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rubric_id", sa.Uuid(), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("structure", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("pacing", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result_schema_override", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rubric_id"], ["rubrics.id"], name="fk_rubric_versions_rubric_id_rubrics", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], name="fk_rubric_versions_org_id_organizations", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["published_by"], ["users.id"], name="fk_rubric_versions_published_by_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["archived_by"], ["users.id"], name="fk_rubric_versions_archived_by_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_rubric_versions"),
        sa.UniqueConstraint("rubric_id", "version", name="uq_rubric_versions_rubric_version"),
    )
    op.create_index("ix_rubric_versions_org_status", "rubric_versions", ["org_id", "status"], unique=False)

    # Circular: a rubric points at its current version, which points back at it.
    op.create_foreign_key(
        "fk_rubrics_current_version_id_rubric_versions",
        "rubrics",
        "rubric_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    for table in TOUCHED_TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_set_updated_at BEFORE UPDATE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    for table in TOUCHED_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_set_updated_at ON {table}")
    op.drop_constraint("fk_rubrics_current_version_id_rubric_versions", "rubrics", type_="foreignkey")
    op.drop_index("ix_rubric_versions_org_status", table_name="rubric_versions")
    op.drop_table("rubric_versions")
    op.drop_index("ix_rubrics_org", table_name="rubrics")
    op.drop_table("rubrics")
