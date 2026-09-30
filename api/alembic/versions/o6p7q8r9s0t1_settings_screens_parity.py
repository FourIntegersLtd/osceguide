"""Backend for the retiring client's Settings screens (Part A of the parity plan).

Four things platform-web needs that had no data or route yet:

- A referrer's bank details for payouts (`referral_payout_details`), encrypted
  at rest — see `app.core.secrets_at_rest`. `bank_name` and
  `account_holder_name` are plain columns; `sort_code`/`account_number` are
  Fernet ciphertext.
- Which plan a redeemed referral's purchase was for (`referrals.plan_code`),
  so a referrer's own history can show it without joining into `billing`.
- Custom reading/simulation timers (`users.custom_reading_seconds`,
  `users.custom_simulation_seconds`), gated by `users.needs_extra_time` —
  together the replacement for `extra_reading_percent` on the API surface.
  The old column stays: `app.migration` still reads it off legacy exports.
- `users.exam_time`, the optional time-of-day half of `exam_date`.
"""

import sqlalchemy as sa
from alembic import op

revision = "o6p7q8r9s0t1"
down_revision = "n5o6p7q8r9s0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- A1: referral payout bank details, encrypted at rest ---------------
    op.create_table(
        "referral_payout_details",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("bank_name", sa.String(length=200), nullable=False),
        sa.Column("account_holder_name", sa.String(length=200), nullable=False),
        sa.Column("sort_code_ciphertext", sa.Text(), nullable=False),
        sa.Column("account_number_ciphertext", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_referral_payout_details_user_id_users", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("user_id", name="uq_referral_payout_details_user_id"),
    )

    # --- A2: which plan a redeemed referral's purchase was for -------------
    op.add_column("referrals", sa.Column("plan_code", sa.String(length=64), nullable=True))

    # --- A3: custom timers, gated by a boolean ------------------------------
    op.add_column(
        "users",
        sa.Column("needs_extra_time", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("users", sa.Column("custom_reading_seconds", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("custom_simulation_seconds", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_users_custom_reading_seconds_range",
        "users",
        "custom_reading_seconds IS NULL OR custom_reading_seconds BETWEEN 1 AND 3659",
    )
    op.create_check_constraint(
        "ck_users_custom_simulation_seconds_range",
        "users",
        "custom_simulation_seconds IS NULL OR custom_simulation_seconds BETWEEN 1 AND 3659",
    )

    # --- A4: exam time, the optional other half of exam_date ----------------
    op.add_column("users", sa.Column("exam_time", sa.Time(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "exam_time")
    op.drop_constraint("ck_users_custom_simulation_seconds_range", "users", type_="check")
    op.drop_constraint("ck_users_custom_reading_seconds_range", "users", type_="check")
    op.drop_column("users", "custom_simulation_seconds")
    op.drop_column("users", "custom_reading_seconds")
    op.drop_column("users", "needs_extra_time")
    op.drop_column("referrals", "plan_code")
    op.drop_table("referral_payout_details")
