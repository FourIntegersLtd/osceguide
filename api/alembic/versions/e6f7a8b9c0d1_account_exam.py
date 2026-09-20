"""The exam an account is for.

The retiring client got this from the hostname: `sca.osceguide.com` set an
`appType` that every request carried, so a person was only ever looking at one
exam and there was no switcher anywhere in the product. The platform has one
domain and one workspace, so that fact had nowhere to live, and each screen
went on to derive its own answer from a different source — the dashboard from
what had been attempted, the library from the whole catalogue, peer practice
from the first exam in a list. A trial account, which holds no entitlement at
all, had no answer available to it.

Deliberately a code rather than a foreign key to `exams`. `identity` sits below
`catalog` in the slice order, so it cannot resolve one, and it should not: this
is a preference, not a grant. What somebody may actually open is decided by
their entitlements, and an unresolvable code simply yields no current exam.

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-09-19 00:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: str | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("exam_code", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "exam_code")
