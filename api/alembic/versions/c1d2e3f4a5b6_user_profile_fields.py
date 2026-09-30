"""B2C profile fields on users — exam, accommodations, consumer role.

Revision ID: c1d2e3f4a5b6
Revises: 9299ac6f097c
Create Date: 2026-09-20 00:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("exam_date", sa.Date(), nullable=True))
    op.add_column(
        "users",
        sa.Column("extra_reading_percent", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.create_check_constraint(
        "ck_users_extra_reading_percent",
        "users",
        "extra_reading_percent BETWEEN 0 AND 100",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_extra_reading_percent", "users", type_="check")
    op.drop_column("users", "extra_reading_percent")
    op.drop_column("users", "exam_date")
