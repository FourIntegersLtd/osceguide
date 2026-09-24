"""Whether a referral has been settled, and on whose word.

Referrals are paid outside the product — a bank transfer somebody makes by
hand — so the only thing the app owes is the record of whether that has
happened. The retiring b2c carried a bare `payout_status` flag and nothing
else, which left "when, and who says so" unanswerable the moment anybody
asked. `paid_at`, `paid_by_user_id` and the transfer's own
`payout_reference` are the difference.

The partial index is on redeemed rows only: an unredeemed code is neither
paid nor unpaid, and the staff queue never asks about one.
"""

import sqlalchemy as sa
from alembic import op

revision = "m4n5o6p7q8r9"
down_revision = "l3m4n5o6p7q8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "referrals",
        sa.Column(
            "payout_status", sa.String(length=16), server_default=sa.text("'unpaid'"), nullable=False
        ),
    )
    op.add_column("referrals", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "referrals",
        sa.Column("paid_by_user_id", sa.UUID(), nullable=True),
    )
    op.add_column("referrals", sa.Column("payout_reference", sa.String(length=64), nullable=True))
    op.create_foreign_key(
        "fk_referrals_paid_by_user",
        "referrals",
        "users",
        ["paid_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_referrals_payout_status",
        "referrals",
        ["payout_status"],
        postgresql_where=sa.text("redeemed_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_referrals_payout_status", table_name="referrals")
    op.drop_constraint("fk_referrals_paid_by_user", "referrals", type_="foreignkey")
    op.drop_column("referrals", "payout_reference")
    op.drop_column("referrals", "paid_by_user_id")
    op.drop_column("referrals", "paid_at")
    op.drop_column("referrals", "payout_status")
