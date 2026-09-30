"""Store a media item's specialty in its own column.

The catalogue's specialty facet was read out of `content`, the same document
that holds the paid body, so every listing had to load the body to file an item
it was about to withhold. The facet is public; now it is a column, backfilled
from the document with the rule `media.domain.specialty_of` applies: the first
non-blank string in `specialties`, else a non-blank `specialty`.
"""

import sqlalchemy as sa
from alembic import op

revision = "029f2c0b1966"
down_revision = "s0t1u2v3w4x5"
branch_labels = None
depends_on = None


# A module constant so a test can run the backfill against rows it wrote.
BACKFILL_SQL = """
        UPDATE media_items AS item
        SET specialty = COALESCE(
            (
                SELECT btrim(entry #>> '{}')
                FROM jsonb_array_elements(
                    CASE
                        WHEN jsonb_typeof(item.content -> 'specialties') = 'array'
                        THEN item.content -> 'specialties'
                        ELSE '[]'::jsonb
                    END
                ) WITH ORDINALITY AS listed(entry, position)
                WHERE jsonb_typeof(entry) = 'string' AND btrim(entry #>> '{}') <> ''
                ORDER BY position
                LIMIT 1
            ),
            CASE
                WHEN jsonb_typeof(item.content -> 'specialty') = 'string'
                THEN NULLIF(btrim(item.content ->> 'specialty'), '')
            END
        )
        WHERE jsonb_typeof(item.content -> 'specialties') = 'array'
           OR jsonb_typeof(item.content -> 'specialty') = 'string'
"""


def upgrade() -> None:
    op.add_column("media_items", sa.Column("specialty", sa.Text(), nullable=True))
    op.execute(BACKFILL_SQL)


def downgrade() -> None:
    op.drop_column("media_items", "specialty")
