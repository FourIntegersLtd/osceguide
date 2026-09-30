"""Tags on community questions, as an array column rather than a join table.

The retiring client let an asker tag a question with specialties and the list
screen narrow to a tag; the ported routes dropped both because `posts` had
nowhere to put one. Tags are read with the post and used to narrow a list —
never looked up in their own right, never shared between rows — so they are a
JSONB array on the post, which is how this codebase keeps every other small
document-shaped collection, and one containment clause does the filtering.
A join table would be a second write per question and a join per page for
nothing a tag is asked to do.

Additive: the column arrives NOT NULL with a `'[]'` default, so every row
written before it reads back as an empty list rather than NULL where the code
expects a list. The GIN index is what makes the `tag` filter an index lookup
rather than a scan.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "k2l3m4n5o6p7"
down_revision = "j1k2l3m4n5o6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.create_index("ix_posts_tags", "posts", ["tags"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_posts_tags", table_name="posts")
    op.drop_column("posts", "tags")
