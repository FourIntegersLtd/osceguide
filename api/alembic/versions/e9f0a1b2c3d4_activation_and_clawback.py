"""An invited account's trial counts from activation (S-10); a paid-out referral clawback is a row (S-13).

Additive: two nullable columns. `users.activated_at` is backfilled with `created_at` for every
account that has already been used (signed in, or holds a password), so no trial window moves;
an invitee who has not yet signed in stays null and starts their trial on first sign-in.

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-10-08 22:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e9f0a1b2c3d4"
down_revision: str | None = "d8e9f0a1b2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE users SET activated_at = created_at "
        "WHERE password_hash IS NOT NULL OR last_login_at IS NOT NULL"
    )
    op.add_column(
        "referrals",
        sa.Column(
            "clawback_of_id", sa.Uuid(), sa.ForeignKey("referrals.id", ondelete="SET NULL"), nullable=True
        ),
    )
    op.create_index("uq_referrals_clawback_of", "referrals", ["clawback_of_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_referrals_clawback_of", table_name="referrals")
    op.drop_column("referrals", "clawback_of_id")
    op.drop_column("users", "activated_at")
