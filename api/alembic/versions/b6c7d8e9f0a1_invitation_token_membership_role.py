"""An invitation token remembers the seat it was sent for.

A person holding several seats in one organisation was shown the oldest on the accept page, which
may not be the seat the invitation was for. Null for a plain reset, a practice-access link and any
token issued before this column; the lookup then keeps the oldest-seat rule.

Revision ID: b6c7d8e9f0a1
Revises: f4a5b6c7d8e9
Create Date: 2026-11-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b6c7d8e9f0a1"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("password_reset_tokens", sa.Column("membership_role", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("password_reset_tokens", "membership_role")
