"""Receipts: what a customer is given for a payment.

The payment row stored a Stripe URL and nothing else, so this product could not
produce its own receipt at all — a customer asking for one was sent to Stripe's
page, which shows the card charge and not what they bought.

The name and email are stored on the payment rather than read from the user,
which is deliberate and is how b2c does it: a receipt is evidence of what
happened at the time, so somebody changing their name afterwards must not
change a document their bank has already seen.

Revision ID: e2f3a4b5c6d7
Revises: c9d0e1f2a3b4
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e2f3a4b5c6d7"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("receipt_id", sa.String(length=64), nullable=True))
    op.add_column("payments", sa.Column("customer_email", sa.String(length=320), nullable=True))
    op.add_column("payments", sa.Column("customer_name", sa.String(length=200), nullable=True))
    op.add_column(
        "payments",
        sa.Column("amount_tax_pence", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column("payments", sa.Column("plan_starts_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("payments", sa.Column("plan_ends_at", sa.DateTime(timezone=True), nullable=True))
    # One receipt id per payment, and a receipt id belongs to one payment.
    op.create_unique_constraint("uq_payments_receipt_id", "payments", ["receipt_id"])


def downgrade() -> None:
    op.drop_constraint("uq_payments_receipt_id", "payments", type_="unique")
    for column in (
        "plan_ends_at",
        "plan_starts_at",
        "amount_tax_pence",
        "customer_name",
        "customer_email",
        "receipt_id",
    ):
        op.drop_column("payments", column)
