"""B2C profile fields on users — exam, accommodations, consumer role.

Revision ID: a1b2c3d4e5f6
Revises: 9299ac6f097c
Create Date: 2026-09-20 00:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "9299ac6f097c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("exam_code", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("exam_date", sa.Date(), nullable=True))
    op.add_column(
        "users",
        sa.Column("extra_reading_percent", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "users",
        sa.Column("consumer_role", sa.String(length=32), nullable=False, server_default=sa.text("'user'")),
    )
    op.create_check_constraint(
        "ck_users_extra_reading_percent",
        "users",
        "extra_reading_percent BETWEEN 0 AND 100",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_extra_reading_percent", "users", type_="check")
    op.drop_column("users", "consumer_role")
    op.drop_column("users", "extra_reading_percent")
    op.drop_column("users", "exam_date")
    op.drop_column("users", "exam_code")
