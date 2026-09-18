"""Give the tutor material it can quote, and a citation for it.

Until now `search_material` answered "not available in this deployment": the
tutor could recall a doctor's own history but could not answer "how do I
safety-net chest pain", which is the question they actually ask it. This is
the table that changes that — the study material cut into passages, each with
the vector it is retrieved by.

Derived data, entirely. Every row can be rebuilt from `station_versions` and
`media_items` by the `reindex_material` job, which is why dropping this table
loses nothing but the time to run it again.

`exam_id` cascades on purpose, unlike the `RESTRICT` the other tutor tables
carry. Those hold somebody's history and must not vanish quietly; this one
holds a copy of a catalogue that is being deleted, and passages of an exam
nobody can buy any more are passages nobody may be read.

The index is IVFFlat rather than HNSW: the corpus is thousands of passages, not
millions, and IVFFlat builds in seconds where HNSW takes minutes on every
re-index. `lists = 100` is the pgvector guidance for a table of this size.
A list count that no longer suits the corpus is a `REINDEX`, not a migration.

Revision ID: 7c1e9f40ab52
Revises: d8ca45c0932a
Create Date: 2026-09-18 00:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7c1e9f40ab52"
down_revision: str | None = "d8ca45c0932a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Cosine distance, because the embeddings are normalised and cosine is what
# `text-embedding-3-small` is trained for. The operator class has to match the
# operator the query uses (`<=>`) or the index is simply not consulted.
IVFFLAT_LISTS = 100

# `text-embedding-3-small`. Must match
# `app/features/tutor_memory/vector_column.py`, which the model reads.
EMBEDDING_DIMENSIONS = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "material_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("corpus", sa.String(length=24), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("exam_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("section", sa.String(length=40), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["exam_id"], ["exams.id"], name=op.f("fk_material_chunks_exam_id_exams"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_material_chunks")),
        sa.UniqueConstraint("corpus", "source_id", "chunk_index", name="uq_material_chunks_passage"),
        sa.CheckConstraint(
            "corpus IN ('station', 'summary', 'slide_deck', 'podcast', 'blog')",
            name=op.f("ck_material_chunks_corpus"),
        ),
    )
    # Added in SQL rather than through a column type, so this file needs
    # nothing from `app/` and says the width it means where you can read it.
    op.execute(f"ALTER TABLE material_chunks ADD COLUMN embedding vector({EMBEDDING_DIMENSIONS}) NOT NULL")
    op.create_index("ix_material_chunks_exam", "material_chunks", ["exam_id", "corpus"])
    op.execute(
        "CREATE INDEX ix_material_chunks_embedding ON material_chunks "
        f"USING ivfflat (embedding vector_cosine_ops) WITH (lists = {IVFFLAT_LISTS})"
    )


def downgrade() -> None:
    op.drop_index("ix_material_chunks_embedding", table_name="material_chunks")
    op.drop_index("ix_material_chunks_exam", table_name="material_chunks")
    op.drop_table("material_chunks")
    # The extension stays. Dropping it would take any other table's vector
    # column with it, and an extension nothing uses costs nothing.
