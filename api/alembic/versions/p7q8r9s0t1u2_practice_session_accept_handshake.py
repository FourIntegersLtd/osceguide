"""Peer practice accept/decline handshake (Part C3 of the content-owner plan).

Being matched used to make a session immediately joinable. This adds the
120-second accept window between pairing and joining: each side records when
they accepted, and `accept_expires_at` is when a still-silent side times out.
All three are nullable because every session matched before this migration,
and any session whose pair skips the handshake path entirely, has none of
them set.
"""

import sqlalchemy as sa
from alembic import op

revision = "p7q8r9s0t1u2"
down_revision = "o6p7q8r9s0t1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "practice_sessions", sa.Column("doctor_accepted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "practice_sessions", sa.Column("patient_accepted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "practice_sessions", sa.Column("accept_expires_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("practice_sessions", "accept_expires_at")
    op.drop_column("practice_sessions", "patient_accepted_at")
    op.drop_column("practice_sessions", "doctor_accepted_at")
