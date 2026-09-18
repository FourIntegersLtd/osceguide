"""Let an attempt say which feedback template its marking was narrowed by.

A sitting binds a feedback template, and that template narrows the rubric its
reviewers work through. Marking never saw it: `attempts` sits below `sittings`
in the slice layers, so it cannot walk slot → circuit → sitting to find one,
and the narrowing was silently ignored — an institution's trainees were marked
on the platform's full rubric whatever their sitting said.

The attempt carries the binding instead, set by whoever creates a slot attempt.

Revision ID: d0e1f2a3b4c5
Revises: b8c9d0e1f2a3
Create Date: 2026-09-17 15:30:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: str | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("attempts", sa.Column("feedback_template_version_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_attempts_feedback_template_version_id",
        "attempts",
        "feedback_template_versions",
        ["feedback_template_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_attempts_feedback_template_version_id",
        "attempts",
        type_="foreignkey",
    )
    op.drop_column("attempts", "feedback_template_version_id")
