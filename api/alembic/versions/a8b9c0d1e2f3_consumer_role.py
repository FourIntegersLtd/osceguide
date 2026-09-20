"""B2C consumer admin role on users.

Revision ID: a8b9c0d1e2f3
Revises: e6f7a8b9c0d1
Create Date: 2026-09-20 00:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a8b9c0d1e2f3"
down_revision: str | None = "e6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("consumer_role", sa.String(length=32), nullable=False, server_default=sa.text("'user'")),
    )


def downgrade() -> None:
    op.drop_column("users", "consumer_role")
