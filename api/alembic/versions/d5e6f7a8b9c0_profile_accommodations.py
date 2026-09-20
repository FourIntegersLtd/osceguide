"""An exam date, and the extra reading time somebody is granted.

These columns already landed in `c1d2e3f4a5b6` (earlier on this chain). This
revision stays so later revisions that depend on it keep a stable parent; it
must not add the columns a second time.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-09-19 00:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    return


def downgrade() -> None:
    return
