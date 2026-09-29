"""Give every payment a receipt id, including those taken before receipts existed (B-4).

`payments.receipt_id` arrived nullable (e2f3a4b5c6d7), and only payments settled
after it were minted one, so an older purchase had no receipt its owner could
open or quote to support. Each is given one now, in the settlement's own format
(`billing.receipts.new_receipt_id`: `RCP-<exam>-<8 hex>`), naming the exam the
plan sold, else the exam the purchase granted, else `all`.
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op

from app.features.billing.receipts import new_receipt_id

revision = "e27eb81413ee"
down_revision = "fbe151cbbf1f"
branch_labels = None
depends_on = None

# When neither the plan nor the grant names an exam: legacy's own "every exam" code.
FALLBACK_EXAM = "all"

_MISSING = sa.text(
    """
    SELECT payment.id, NULLIF(plan.exam_code, '') AS plan_exam, exam.code AS granted_exam
    FROM payments AS payment
    LEFT JOIN plans AS plan ON plan.id = payment.plan_id
    LEFT JOIN entitlements AS grant_row ON grant_row.id = payment.entitlement_id
    LEFT JOIN exams AS exam ON exam.id = grant_row.exam_id
    WHERE payment.receipt_id IS NULL
    ORDER BY payment.paid_at, payment.id
    """
)


def backfill(connection: Any) -> int:
    """Mint a receipt id for every payment without one; returns how many were written.

    Ids already taken are read first, so a new one never collides with an old
    one or with another minted in this run.
    """
    taken = set(
        connection.execute(sa.text("SELECT receipt_id FROM payments WHERE receipt_id IS NOT NULL")).scalars()
    )
    written = 0
    for payment_id, plan_exam, granted_exam in connection.execute(_MISSING).all():
        receipt_id = new_receipt_id(plan_exam or granted_exam or FALLBACK_EXAM)
        while receipt_id in taken:
            receipt_id = new_receipt_id(plan_exam or granted_exam or FALLBACK_EXAM)
        taken.add(receipt_id)
        connection.execute(
            sa.text("UPDATE payments SET receipt_id = :receipt_id WHERE id = :payment_id"),
            {"receipt_id": receipt_id, "payment_id": payment_id},
        )
        written += 1
    return written


def upgrade() -> None:
    backfill(op.get_bind())


def downgrade() -> None:
    # Nothing to undo: an id a customer may already have quoted is not taken back.
    pass
