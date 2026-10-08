"""A decision's free text may be scrubbed on erasure (S-20), and nothing else may change.

`reject_result_mutation` refused every update. It now lets one through on
`candidate_result_revisions`: the update that replaces `rationale` and `moderation_notes` with
`[erased]` (null stays null) and leaves every other column as it was. Deletes and every other
update are still refused, and `candidate_result_events` is untouched.

Revision ID: 7d3e9c1a5b42
Revises: f0a1b2c3d4e5
Create Date: 2026-10-09 01:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "7d3e9c1a5b42"
down_revision: str | None = "f0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_REFUSE = """
    CREATE OR REPLACE FUNCTION reject_result_mutation() RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION '% is append-only; supersede the revision instead', TG_TABLE_NAME
            USING ERRCODE = '55000';
    END;
    $$ LANGUAGE plpgsql
"""

_ALLOW_TEXT_ERASURE = """
    CREATE OR REPLACE FUNCTION reject_result_mutation() RETURNS trigger AS $$
    BEGIN
        IF TG_OP = 'UPDATE' AND TG_TABLE_NAME = 'candidate_result_revisions'
           AND (to_jsonb(NEW) - 'rationale' - 'moderation_notes')
               = (to_jsonb(OLD) - 'rationale' - 'moderation_notes')
           AND (NEW.rationale IS NULL) = (OLD.rationale IS NULL)
           AND (NEW.rationale IS NULL OR NEW.rationale = '[erased]')
           AND (NEW.moderation_notes IS NULL) = (OLD.moderation_notes IS NULL)
           AND (NEW.moderation_notes IS NULL OR NEW.moderation_notes = '[erased]')
        THEN
            RETURN NEW;
        END IF;
        RAISE EXCEPTION '% is append-only; supersede the revision instead', TG_TABLE_NAME
            USING ERRCODE = '55000';
    END;
    $$ LANGUAGE plpgsql
"""


def upgrade() -> None:
    op.execute(_ALLOW_TEXT_ERASURE)


def downgrade() -> None:
    op.execute(_REFUSE)
