"""Bind a feedback template to the rubric it narrows, and let the platform own one.

A feedback template said which fields of "the platform marking schema" its
reviewers work through, where that schema was whichever of four hand-written
JSON files the template's exam happened to bind. Nothing could check the
selection, so a template could name a domain no schema had and the reviews
built on it could never be completed.

It now names a rubric version outright, and the selection is validated against
that rubric's own domains when it is written.

`owner_kind` is the second half: these were `org_id NOT NULL`, so the platform
could not narrow its own rubric for its own reviewers — the same asymmetry
`stations` did not have.

Existing rows keep the owner they had and are pointed at a published platform
rubric; a database holding templates with no rubric to bind them to is refused
rather than guessed at.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-17 15:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OWNER_MATCHES_ORG = (
    "(owner_kind = 'platform' AND org_id IS NULL) OR (owner_kind = 'org' AND org_id IS NOT NULL)"
)

TABLES = ("feedback_templates", "feedback_template_versions")


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

    op.add_column("feedback_templates", sa.Column("rubric_version_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_feedback_templates_rubric_version_id_rubric_versions",
        "feedback_templates",
        "rubric_versions",
        ["rubric_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.execute(
        "UPDATE feedback_templates SET rubric_version_id = ("
        "  SELECT id FROM rubric_versions"
        "  WHERE org_id IS NULL AND status = 'published'"
        "  ORDER BY created_at LIMIT 1"
        ") WHERE rubric_version_id IS NULL"
    )
    # A template with nothing to narrow is not a template. Rather than invent a
    # rubric, say so: this only fires where templates exist and no rubric does.
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM feedback_templates WHERE rubric_version_id IS NULL) THEN "
        "RAISE EXCEPTION 'feedback_templates exist with no published platform rubric to narrow. "
        "Author and publish one, then re-run this migration.'; "
        "END IF; END $$"
    )
    op.alter_column("feedback_templates", "rubric_version_id", existing_type=sa.Uuid(), nullable=False)

    # An exam no longer has anything to say about a feedback template.
    op.drop_constraint("fk_feedback_templates_exam_id_exams", "feedback_templates", type_="foreignkey")
    op.drop_column("feedback_templates", "exam_id")


def downgrade() -> None:
    op.add_column("feedback_templates", sa.Column("exam_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_feedback_templates_exam_id_exams",
        "feedback_templates",
        "exams",
        ["exam_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint(
        "fk_feedback_templates_rubric_version_id_rubric_versions",
        "feedback_templates",
        type_="foreignkey",
    )
    op.drop_column("feedback_templates", "rubric_version_id")
    for table in TABLES:
        op.drop_constraint(f"ck_{table}_owner_matches_org", table, type_="check")
        op.execute(f"DELETE FROM {table} WHERE org_id IS NULL")
        op.alter_column(table, "org_id", existing_type=sa.Uuid(), nullable=False)
        op.drop_column(table, "owner_kind")
