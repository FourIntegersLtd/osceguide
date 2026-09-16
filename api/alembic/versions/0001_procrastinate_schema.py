"""procrastinate job queue schema

Revision ID: 0001
Revises:
Create Date: 2026-09-15
"""

from __future__ import annotations

from collections.abc import Sequence
from importlib import resources

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The job queue's tables, ship with the procrastinate package. Applying it
    # here means every environment gets the queue with the rest of the schema.
    schema_sql = resources.files("procrastinate.sql").joinpath("schema.sql").read_text()
    op.execute(schema_sql)


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS procrastinate CASCADE")
    for name in (
        "procrastinate_jobs",
        "procrastinate_events",
        "procrastinate_periodic_defers",
        "procrastinate_workers",
        "procrastinate_job_lock",
    ):
        op.execute(f"DROP TABLE IF EXISTS {name} CASCADE")
