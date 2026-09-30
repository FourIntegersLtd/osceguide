"""Let a station comment exist.

`ck_posts_parent_matches_kind` said every post that is not a question has a
parent. A station comment has a station and no parent, so
`POST /stations/{id}/comments` violated it on every call. The constraint now
names the three shapes.

Revision ID: b2c3d4e5f6a7
Revises: c1d2e3f4a5b6
Create Date: 2026-09-17 10:05:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NAME = "ck_posts_ck_posts_parent_matches_kind"
OLD = "(kind = 'question' AND parent_id IS NULL) OR (kind <> 'question' AND parent_id IS NOT NULL)"
NEW = (
    "(kind = 'question' AND parent_id IS NULL)"
    " OR (kind = 'reply' AND parent_id IS NOT NULL)"
    " OR (kind = 'comment' AND parent_id IS NULL AND station_id IS NOT NULL)"
)


def upgrade() -> None:
    op.drop_constraint(op.f(NAME), "posts", type_="check")
    op.create_check_constraint(op.f(NAME), "posts", NEW)


def downgrade() -> None:
    op.drop_constraint(op.f(NAME), "posts", type_="check")
    op.create_check_constraint(op.f(NAME), "posts", OLD)
