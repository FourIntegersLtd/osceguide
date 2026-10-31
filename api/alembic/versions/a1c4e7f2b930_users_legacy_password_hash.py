"""Carry a legacy b2c bcrypt hash beside the argon2 one.

A nullable column, so the release before this one runs against it unchanged. It is read only at
sign-in, accepted once and replaced with argon2id; dropping it (with its verifier) is how the
legacy backends are decommissioned.

Revision ID: a1c4e7f2b930
Revises: 9b3d5e71c2a8
Create Date: 2026-10-31 00:00:00+00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a1c4e7f2b930"
down_revision = "9b3d5e71c2a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("legacy_password_hash", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "legacy_password_hash")
