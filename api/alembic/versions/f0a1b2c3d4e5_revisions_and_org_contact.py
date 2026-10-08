"""Edits carry a revision (B-15); an organisation keeps a contact (B-33).

Additive: a `revision` integer (default 1) on trainees, sittings, circuits, rubric_versions and exams,
and two nullable contact columns on organizations.

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-10-08 23:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f0a1b2c3d4e5"
down_revision: str | None = "e9f0a1b2c3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_REVISIONED = ("trainees", "sittings", "circuits", "rubric_versions", "exams")


def upgrade() -> None:
    for table in _REVISIONED:
        op.add_column(table, sa.Column("revision", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("organizations", sa.Column("contact_name", sa.String(length=200), nullable=True))
    op.add_column("organizations", sa.Column("contact_email", sa.String(length=320), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "contact_email")
    op.drop_column("organizations", "contact_name")
    for table in reversed(_REVISIONED):
        op.drop_column(table, "revision")
