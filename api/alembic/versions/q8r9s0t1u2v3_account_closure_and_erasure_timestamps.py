"""Account closure and erasure timestamps (E-4, retention).

`close_account` used to leave no record of when it happened, so a scheduled
erasure job would have had nothing to measure "30 days ago" against. This adds
`closed_at`, written the moment an account is closed, and `erased_at`, written
the moment the erasure job scrubs it — the second timestamp is also the job's
idempotency check, so a re-run does not re-scrub or double-count an already
erased account.
"""

import sqlalchemy as sa
from alembic import op

revision = "q8r9s0t1u2v3"
down_revision = "p7q8r9s0t1u2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("erased_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "erased_at")
    op.drop_column("users", "closed_at")
