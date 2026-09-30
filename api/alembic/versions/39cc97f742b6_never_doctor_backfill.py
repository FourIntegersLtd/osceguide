"""Carry b2c's never-the-doctor list over as data (P-2).

b2c's matcher hardcoded three addresses that must always take the patient's
part (`human_practice_service.assign_roles`, `always_patient_emails`).
`practice_history.never_doctor` replaced the list (a15563fea7ac) but arrived
with a default of false and nothing set it, so those three accounts started
being offered the doctor's part. Each existing account with one of those
addresses gets a history row with the flag set; a row it already has keeps its
role and count.
"""

from alembic import op

revision = "39cc97f742b6"
down_revision = "e27eb81413ee"
branch_labels = None
depends_on = None

# Verbatim from b2c's matcher.
NEVER_DOCTOR_EMAILS = ("y.hkehinde@yahoo.com", "sheinat03@gmail.com", "hello@fourintegers.com")

# A module constant so a test can run the backfill against rows it wrote.
BACKFILL_SQL = """
    INSERT INTO practice_history (id, user_id, never_doctor)
    SELECT gen_random_uuid(), users.id, true
    FROM users
    WHERE lower(users.email::text) IN ({addresses})
    ON CONFLICT (user_id) DO UPDATE SET never_doctor = true
""".format(addresses=", ".join(f"'{address}'" for address in NEVER_DOCTOR_EMAILS))


def upgrade() -> None:
    op.execute(BACKFILL_SQL)


def downgrade() -> None:
    # Left set: clearing it would put these people back in the doctor's chair,
    # and nothing records which rows this migration created.
    pass
