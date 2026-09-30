"""Allow the shared help corpus in material_chunks.

The tutor-memory index gained a `help` corpus — product help passages every
exam shares — but `ck_material_chunks_corpus` still listed only the original
five, so indexing help refused every row. Widens the check to match
`tutor_memory/models.py`.

Revision ID: v3w4x5y6z7a8
Revises: u2v3w4x5y6z7
Create Date: 2026-10-01
"""

from alembic import op

revision = "v3w4x5y6z7a8"
down_revision = "u2v3w4x5y6z7"
branch_labels = None
depends_on = None

_CONSTRAINT = "ck_material_chunks_corpus"
_TABLE = "material_chunks"


# Raw SQL so the constraint name is exactly what is written here, out of
# reach of the naming convention (which would prefix it a second time).
def upgrade() -> None:
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT {_CONSTRAINT}")
    op.execute(
        f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_CONSTRAINT} "
        "CHECK (corpus IN ('station', 'summary', 'slide_deck', 'podcast', 'blog', 'help'))"
    )


def downgrade() -> None:
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT {_CONSTRAINT}")
    op.execute(
        f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_CONSTRAINT} "
        "CHECK (corpus IN ('station', 'summary', 'slide_deck', 'podcast', 'blog'))"
    )
