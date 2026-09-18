"""Let an institution write its own exams.

An exam was platform-owned by construction: `exams` had no owner column, so the
only exam an institution could run was one we had published, and a programme
was a label on a row we happened to have written. That made the B2B arm wait on
the B2C catalogue. It is the wrong dependency — a medical school's finals OSCE
is not our product, and our consumer exams are not theirs to wait for.

`owner_kind` and `org_id` are the same split `stations` and `rubrics` already
carry. A platform exam (`org_id IS NULL`) is the consumer catalogue. An org exam
is that institution's own: written, published and retired on its own schedule,
invisible outside it, and never in the B2C listing.

The unique constraint on `code` goes with it. A code is unique **within an
owner**, not globally, so two schools may both have a `finals` and a school may
have its own `plab` alongside ours. Keeping one namespace would have let
whoever registered a code first reserve it for every institution on the
platform.

Every existing row is a platform exam, which is what it already was.

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-09-17 00:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3a4b5c6d7e8"
down_revision: str | None = "e2f3a4b5c6d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "exams",
        sa.Column("owner_kind", sa.String(length=16), nullable=False, server_default=sa.text("'platform'")),
    )
    op.add_column("exams", sa.Column("org_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_exams_org_id_organizations",
        "exams",
        "organizations",
        ["org_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(
        "ck_exams_owner_matches_org",
        "exams",
        "(owner_kind = 'platform' AND org_id IS NULL) OR (owner_kind = 'org' AND org_id IS NOT NULL)",
    )

    # One global namespace becomes one per owner. The platform half keeps the
    # old guarantee; the org half scopes it to the organisation.
    op.drop_constraint("uq_exams_code", "exams", type_="unique")
    op.create_index(
        "uq_exams_platform_code",
        "exams",
        ["code"],
        unique=True,
        postgresql_where=sa.text("org_id IS NULL"),
    )
    op.create_index(
        "uq_exams_org_code",
        "exams",
        ["org_id", "code"],
        unique=True,
        postgresql_where=sa.text("org_id IS NOT NULL"),
    )


def downgrade() -> None:
    # Org-owned exams have no representation in the old shape, and a programme
    # or a sitting may already point at one. Dropping them would take live rows
    # with it, so the downgrade refuses rather than deciding that quietly.
    conn = op.get_bind()
    owned = conn.execute(sa.text("SELECT count(*) FROM exams WHERE org_id IS NOT NULL")).scalar_one()
    if owned:
        raise RuntimeError(
            f"{owned} organisation-owned exam(s) exist. They cannot be expressed in the "
            "single-namespace shape this downgrade restores; remove them deliberately first."
        )

    op.drop_index("uq_exams_org_code", table_name="exams")
    op.drop_index("uq_exams_platform_code", table_name="exams")
    op.create_unique_constraint("uq_exams_code", "exams", ["code"])
    op.drop_constraint("ck_exams_owner_matches_org", "exams", type_="check")
    op.drop_constraint("fk_exams_org_id_organizations", "exams", type_="foreignkey")
    op.drop_column("exams", "org_id")
    op.drop_column("exams", "owner_kind")
