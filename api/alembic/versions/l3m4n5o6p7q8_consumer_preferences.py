"""Consumer preferences and whether a peer would practise again.

The settings tab kept one of four checkboxes because the other three had no
column. Closing an account does not need a column: `users.status` already
refuses a sign-in that is not `active`. Peer feedback already accepted
`would_practice_again` on the request and then dropped it.
"""

import sqlalchemy as sa
from alembic import op

revision = "l3m4n5o6p7q8"
down_revision = "k2l3m4n5o6p7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("ai_training_consent", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("colleague_waiting_email", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("replay_onboarding", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("practice_sessions", sa.Column("would_practice_again", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("practice_sessions", "would_practice_again")
    op.drop_column("users", "replay_onboarding")
    op.drop_column("users", "colleague_waiting_email")
    op.drop_column("users", "ai_training_consent")
