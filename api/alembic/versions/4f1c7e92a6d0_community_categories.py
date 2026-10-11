"""Community posts get a category, and a post may be written by the assistant.

`category` is general, platform, skills or exam (a question's free-text tags become its
subtags). Existing posts that name an exam are backfilled to `exam`; the rest are `general`.
`is_assistant` marks a reply the OSCE Guide assistant wrote, which has no author account, so
`author_id` becomes nullable. Only adds or relaxes, so a rollback keeps the new schema.

Revision ID: 4f1c7e92a6d0
Revises: 7a965853ec61
Create Date: 2026-10-11
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "4f1c7e92a6d0"
down_revision = "7a965853ec61"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("category", sa.String(16), nullable=False, server_default="general"))
    op.add_column("posts", sa.Column("is_assistant", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("posts", "author_id", existing_type=sa.Uuid(), nullable=True)
    op.execute("UPDATE posts SET category = 'exam' WHERE exam_id IS NOT NULL")
    op.create_index("ix_posts_category_created", "posts", ["category", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_posts_category_created", table_name="posts")
    op.drop_column("posts", "is_assistant")
    op.drop_column("posts", "category")
