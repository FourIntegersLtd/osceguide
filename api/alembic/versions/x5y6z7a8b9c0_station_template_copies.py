"""Add station_templates.copied_from_id: the platform template an organisation's copy was made from.

Copying the standard template twice gave an organisation two copies, and the
import dialog found the organisation's copy by its title, which the
organisation may change. The column names the source, and a partial unique
index keeps one copy per source per organisation. Add-only.

Revision ID: x5y6z7a8b9c0
Revises: w4x5y6z7a8b9
Create Date: 2026-10-01
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "x5y6z7a8b9c0"
down_revision = "w4x5y6z7a8b9"
branch_labels = None
depends_on = None

_TABLE = "station_templates"
_INDEX = "uq_station_templates_org_copied_from"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "copied_from_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("station_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        _INDEX,
        _TABLE,
        ["org_id", "copied_from_id"],
        unique=True,
        postgresql_where=sa.text("copied_from_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(_INDEX, table_name=_TABLE)
    op.drop_column(_TABLE, "copied_from_id")
