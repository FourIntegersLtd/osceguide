"""Each partner pilot's cost per click and spend alert thresholds (G-1).

Ported from b2c's `partner_pilot_config` Firestore collection. One row per
partner, written the first time an admin edits it; until then the b2c defaults
apply in code, so an empty table changes nothing.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "40c4e90d0cd4"
down_revision: str | None = "39cc97f742b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "partner_pilot_configs",
        sa.Column("partner", sa.String(length=32), nullable=False),
        sa.Column("cost_per_click_pence", sa.Integer(), nullable=False),
        sa.Column("spend_alert_thresholds_pence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("spend_alert_recipients", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("last_alerted_threshold_pence", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_partner_pilot_configs")),
        sa.UniqueConstraint("partner", name="uq_partner_pilot_configs_partner"),
    )


def downgrade() -> None:
    op.drop_table("partner_pilot_configs")
