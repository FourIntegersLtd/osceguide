"""Retrieve the tutor's material through HNSW rather than IVFFlat.

IVFFlat sorts the passages into lists when the index is built and reads only a
few of them per question, so a passage in a list that was not read is not
found, and the lists drift out of true as the material changes after the build.
On staging the one list probed for "red flags for chest pain" held no summary at
all. HNSW has no build-time clustering to go stale and finds more of the true
nearest passages at the same speed.

`m = 24` and `ef_construction = 200` are above pgvector's defaults (16 and 64):
a denser graph, built more carefully, for recall over build time. The corpus is
thousands of passages, so the build is still seconds. How hard a query searches
is set per query in `tutor_memory/repository_index.py`, not here.

The index keeps its name and the column is untouched, so the release before
this one runs against it unchanged.

Revision ID: y6z7a8b9c0d1
Revises: x5y6z7a8b9c0
Create Date: 2026-10-04 00:00:00+00:00
"""

from __future__ import annotations

from alembic import op

revision = "y6z7a8b9c0d1"
down_revision = "x5y6z7a8b9c0"
branch_labels = None
depends_on = None

HNSW_M = 24
HNSW_EF_CONSTRUCTION = 200
IVFFLAT_LISTS = 100


def upgrade() -> None:
    op.drop_index("ix_material_chunks_embedding", table_name="material_chunks")
    op.execute(
        "CREATE INDEX ix_material_chunks_embedding ON material_chunks "
        "USING hnsw (embedding vector_cosine_ops) "
        f"WITH (m = {HNSW_M}, ef_construction = {HNSW_EF_CONSTRUCTION})"
    )


def downgrade() -> None:
    op.drop_index("ix_material_chunks_embedding", table_name="material_chunks")
    op.execute(
        "CREATE INDEX ix_material_chunks_embedding ON material_chunks "
        f"USING ivfflat (embedding vector_cosine_ops) WITH (lists = {IVFFLAT_LISTS})"
    )
