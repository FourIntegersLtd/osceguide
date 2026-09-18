"""Let social content be addressed to a room, not just an exam.

Questions, practice slots and queue places were addressed to an exam and
nothing else, so every one of them sat in a single global pool. An
institution's trainees had no way to talk among themselves, and a teaching
group had no way to practise together.

Each of the three gains the same three columns and the same CHECK. The check
is the point: without it a row can claim to be private while naming nobody,
which reads as public to the filter and publishes the conversation.

Existing rows become `public`, which is what they already were.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-17 12:15:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUDIENCE_CHECK = (
    "(visibility = 'public' AND audience_org_id IS NULL AND audience_group_id IS NULL)"
    " OR (visibility = 'organisation' AND audience_org_id IS NOT NULL AND audience_group_id IS NULL)"
    " OR (visibility = 'group' AND audience_org_id IS NOT NULL AND audience_group_id IS NOT NULL)"
)

# table, the column its audience indexes pair with
TABLES = (
    ("posts", "created_at"),
    ("availability_posts", "starts_at"),
    ("practice_queue_entries", None),
)


def upgrade() -> None:
    for table, sort_column in TABLES:
        op.add_column(
            table,
            sa.Column("visibility", sa.String(16), nullable=False, server_default=sa.text("'public'")),
        )
        op.add_column(table, sa.Column("audience_org_id", sa.Uuid(), nullable=True))
        op.add_column(table, sa.Column("audience_group_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            op.f(f"fk_{table}_audience_org_id_organizations"),
            table,
            "organizations",
            ["audience_org_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_foreign_key(
            op.f(f"fk_{table}_audience_group_id_trainee_groups"),
            table,
            "trainee_groups",
            ["audience_group_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_check_constraint(op.f(f"ck_{table}_ck_{table}_audience"), table, AUDIENCE_CHECK)
        if sort_column is not None:
            op.create_index(
                op.f(f"ix_{table}_audience_org_id"), table, ["audience_org_id", sort_column]
            )
            op.create_index(
                op.f(f"ix_{table}_audience_group_id"), table, ["audience_group_id", sort_column]
            )


def downgrade() -> None:
    for table, sort_column in TABLES:
        if sort_column is not None:
            op.drop_index(op.f(f"ix_{table}_audience_group_id"), table_name=table)
            op.drop_index(op.f(f"ix_{table}_audience_org_id"), table_name=table)
        op.drop_constraint(op.f(f"ck_{table}_ck_{table}_audience"), table, type_="check")
        op.drop_constraint(op.f(f"fk_{table}_audience_group_id_trainee_groups"), table, type_="foreignkey")
        op.drop_constraint(op.f(f"fk_{table}_audience_org_id_organizations"), table, type_="foreignkey")
        op.drop_column(table, "audience_group_id")
        op.drop_column(table, "audience_org_id")
        op.drop_column(table, "visibility")
