"""An exam date, and the extra reading time somebody is granted.

Two fields the ported screens needed and could not read anywhere.

`exam_date`: the consumer dashboard counts down to it, and the exam-wishes
prompt appears in the week before. Both came across and neither had a source,
so the countdown was left off rather than shown against a date we invented.

`extra_reading_percent`: the retiring client read a bare
`accessibility.needs_extra_reading_time` boolean off the user and extended the
clock from inside the timer component. A percentage says what was actually
granted rather than implying a fixed amount, and 25 is what a bare "yes" meant.

It applies to a person's own practice. It is deliberately **not** applied to an
institution's examination: a circuit's clock is one clock for everybody on it,
and extending it for one candidate extends it for the rest.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-09-19 00:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("exam_date", sa.Date(), nullable=True))
    op.add_column(
        "users",
        sa.Column("extra_reading_percent", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    # An arrangement outside 0-100% is a typo, and a negative one would shorten
    # somebody's reading time — the opposite of what the field is for.
    op.create_check_constraint(
        "ck_users_extra_reading_percent",
        "users",
        "extra_reading_percent BETWEEN 0 AND 100",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_extra_reading_percent", "users", type_="check")
    op.drop_column("users", "extra_reading_percent")
    op.drop_column("users", "exam_date")
