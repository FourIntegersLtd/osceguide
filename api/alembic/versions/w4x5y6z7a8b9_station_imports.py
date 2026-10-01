"""Add station_imports: an uploaded station document and what was drafted from it.

An institution that already has a station library uploads each station as a PDF
or Word file. The row holds the document's text and how far the two drafting
jobs have got: a template first, then a station on that template. Add-only.

Revision ID: w4x5y6z7a8b9
Revises: v3w4x5y6z7a8
Create Date: 2026-10-01
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "w4x5y6z7a8b9"
down_revision = "v3w4x5y6z7a8"
branch_labels = None
depends_on = None

_TABLE = "station_imports"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_kind", sa.String(16), nullable=False),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("exam_code", sa.String(32), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False, server_default=sa.text("''")),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("station_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "template_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("station_template_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "station_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("stations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("review_notes", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "(owner_kind = 'platform' AND org_id IS NULL) OR (owner_kind = 'org' AND org_id IS NOT NULL)",
            name="ck_station_imports_owner_matches_org",
        ),
    )
    op.create_index("ix_station_imports_org_created_at", _TABLE, ["org_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_station_imports_org_created_at", table_name=_TABLE)
    op.drop_table(_TABLE)
