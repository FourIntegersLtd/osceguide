"""Give an imported attempt a reference back to where it came from.

The import must be re-runnable: a partial run, a fixed transform and a second
pass should update nothing rather than duplicate somebody's history. Without
an identity that survives the transform there is no way to tell an attempt
already imported from a new one.

Partial, because every attempt created since the cutover has no legacy id and
they would otherwise all collide on NULL.

Dropped along with `app/migration/` once every tenant is across.

Revision ID: 9299ac6f097c
Revises: 03255ac3246c
Create Date: 2026-09-16 13:36:05.794614+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '9299ac6f097c'
down_revision: str | None = '03255ac3246c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('attempts', sa.Column('legacy_ref', sa.String(length=200), nullable=True))
    op.create_index('uq_attempts_legacy_ref', 'attempts', ['legacy_ref'], unique=True, postgresql_where=sa.text('legacy_ref IS NOT NULL'))


def downgrade() -> None:
    op.drop_index('uq_attempts_legacy_ref', table_name='attempts', postgresql_where=sa.text('legacy_ref IS NOT NULL'))
    op.drop_column('attempts', 'legacy_ref')
