"""Let an exam be written rather than seeded.

Four exams were inserted by the migration that created the table, mirrored by a
frozen tuple in `catalog.domain`, and pinned to it by a unit test. `resolve_exam`
checked the tuple *before* it read the table, so a row inserted by any other
means was unreachable: the platform could not add an exam to its own product
without a code change and a release.

The tuple is gone and so is the seed. An exam is now created through
`POST /platform/exams` by a platform admin, and it names the rubric version it
is marked against instead of a `framework_id` string that had to match one of
four frameworks the engine shipped.

The four seeded rows are removed only where nothing references them, so a
deployed environment that has already built on them keeps them — they will
simply be drafts until an admin names a rubric and publishes them. A fresh
database ends up with an empty table, which is the intent.

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-09-17 14:30:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The rows the old seed inserted. Removed where nothing points at them.
SEEDED_CODES = ("sca", "plab", "casc", "ortho")

# Every table that takes an exam by id, so a seeded exam in use is left alone
# rather than failing the migration on a RESTRICT.
REFERRING_TABLES = ("stations", "org_programmes", "attempts", "entitlements", "station_sets")


def upgrade() -> None:
    op.add_column(
        "exams",
        sa.Column("status", sa.String(length=32), server_default=sa.text("'draft'"), nullable=False),
    )
    op.add_column("exams", sa.Column("rubric_version_id", sa.Uuid(), nullable=True))
    op.add_column(
        "exams",
        sa.Column("partner_pilot", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_foreign_key(
        "fk_exams_rubric_version_id_rubric_versions",
        "exams",
        "rubric_versions",
        ["rubric_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_exams_published_has_rubric",
        "exams",
        "status <> 'published' OR rubric_version_id IS NOT NULL",
    )

    # Anything that already exists was being offered, so it keeps being offered
    # — but only if it can be, and none of them can until a rubric is named.
    # They become drafts, which is the honest description of an exam with no
    # rubric behind it.
    op.drop_column("exams", "framework_id")
    op.drop_column("exams", "feedback_model_key")

    unused = " AND ".join(
        f"NOT EXISTS (SELECT 1 FROM {table} WHERE {table}.exam_id = exams.id)"
        for table in REFERRING_TABLES
    )
    op.execute(
        sa.text(f"DELETE FROM exams WHERE code = ANY(:codes) AND {unused}").bindparams(
            sa.bindparam("codes", value=list(SEEDED_CODES))
        )
    )


def downgrade() -> None:
    op.add_column(
        "exams",
        sa.Column("feedback_model_key", sa.String(length=64), server_default=sa.text("'default'"), nullable=False),
    )
    op.add_column("exams", sa.Column("framework_id", sa.String(length=64), server_default="", nullable=False))
    op.drop_constraint("ck_exams_published_has_rubric", "exams", type_="check")
    op.drop_constraint("fk_exams_rubric_version_id_rubric_versions", "exams", type_="foreignkey")
    op.drop_column("exams", "partner_pilot")
    op.drop_column("exams", "rubric_version_id")
    op.drop_column("exams", "status")
