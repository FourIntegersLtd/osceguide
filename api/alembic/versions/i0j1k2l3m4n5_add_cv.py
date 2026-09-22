"""A learner's uploaded CV, read into sections.

The PDF is not stored: its text is pulled on upload and the structured result
is what the product reads back. `created_at` (from the `Timestamps` mixin) is
the upload time the list sorts by.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "i0j1k2l3m4n5"
down_revision = "h9i0j1k2l3m4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cvs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'processing'"), nullable=False),
        sa.Column("original_filename", sa.String(length=255), server_default=sa.text("''"), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("structured", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cvs_user_id", "cvs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_cvs_user_id", table_name="cvs")
    op.drop_table("cvs")
