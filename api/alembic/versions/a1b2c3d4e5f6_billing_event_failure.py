"""Keep the reason a Stripe delivery was not applied.

A payment for an address we do not know was meant to be "recorded as an
unprocessed event rather than dropped", but the error that refused it rolled
the ledger row back with everything else. Nothing was left to reconcile. The
row now survives, carrying why.

Revision ID: a1b2c3d4e5f6
Revises: 9299ac6f097c
Create Date: 2026-09-17 10:00:00+00:00
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
    op.add_column("stripe_events", sa.Column("failure", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("stripe_events", "failure")
