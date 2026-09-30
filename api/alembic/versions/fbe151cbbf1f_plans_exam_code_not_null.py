"""A plan must name the exam it sells (B-2).

A plan with no exam used to default to SCA at settlement, which granted the
wrong thing; the settlement now refuses it, but the column still let one be
written and listed for sale. Any row already missing an exam is kept, taken off
sale, and given an empty code — which settlement already refuses exactly as it
refused the null — so a charge can never again land on a plan that grants
nothing. Then the column is made NOT NULL.
"""

from alembic import op

revision = "fbe151cbbf1f"
down_revision = "5704ed78c1f2"
branch_labels = None
depends_on = None

# A module constant so a test can run the backfill against rows it wrote.
BACKFILL_SQL = "UPDATE plans SET exam_code = '', active = false WHERE exam_code IS NULL"


def upgrade() -> None:
    op.execute(BACKFILL_SQL)
    op.alter_column("plans", "exam_code", nullable=False)


def downgrade() -> None:
    op.alter_column("plans", "exam_code", nullable=True)
