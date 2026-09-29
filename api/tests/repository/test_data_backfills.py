"""The data a migration rewrites on its way up, checked row by row.

A schema change is proved by the drift test; a backfill is not, because the
test database is migrated while it is empty. Each migration that rewrites rows
keeps its SQL in a module constant, and these tests run that SQL against rows
written here, so the rule it applies is checked against the Python it mirrors.
"""

from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.db

VERSIONS = Path(__file__).resolve().parents[2] / "alembic" / "versions"


def migration(revision: str) -> ModuleType:
    """Load one migration module by its revision id; the filenames start with digits."""
    (path,) = VERSIONS.glob(f"{revision}_*.py")
    spec = importlib.util.spec_from_file_location(f"migration_{revision}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MEDIA_DOCUMENTS: list[dict[str, Any]] = [
    {"specialties": ["Cardiology", "Respiratory"], "specialty": "Respiratory"},
    {"specialties": ["  ", 7, " Renal "]},
    {"specialties": "Cardiology", "specialty": " Neurology "},
    {"specialty": "   "},
    {"specialty": 12},
    {"slides": ["Angina"]},
]


async def test_the_media_specialty_backfill_files_items_as_the_reader_does(db_session: AsyncSession) -> None:
    """The column is filled with exactly what `specialty_of` reads out of the document."""
    from app.features.media.domain import specialty_of
    from app.features.media.models import MediaItem

    items = [
        MediaItem(kind="summary", slug=f"backfill-{uuid.uuid4().hex[:8]}", title="T", content=document)
        for document in MEDIA_DOCUMENTS
    ]
    db_session.add_all(items)
    await db_session.flush()
    item_ids = [item.id for item in items]
    await db_session.execute(update(MediaItem).where(MediaItem.id.in_(item_ids)).values(specialty=None))

    await db_session.execute(text(migration("029f2c0b1966").BACKFILL_SQL))

    stored = dict(
        (
            await db_session.execute(
                select(MediaItem.id, MediaItem.specialty).where(MediaItem.id.in_(item_ids))
            )
        ).all()
    )
    assert [stored[item_id] for item_id in item_ids] == [
        specialty_of(document) for document in MEDIA_DOCUMENTS
    ]
    assert [stored[item_id] for item_id in item_ids] == ["Cardiology", "Renal", "Neurology", None, None, None]


async def test_a_plan_with_no_exam_is_taken_off_sale_before_the_column_is_required(
    db_session: AsyncSession,
) -> None:
    """B-2: a null exam becomes '' (which settlement refuses as it refused null) and
    the plan stops being sold; a plan that names its exam is left alone."""
    from sqlalchemy.exc import IntegrityError

    from app.features.billing.models import Plan

    # The constraint is what the migration adds; lifted here, inside this test's
    # own transaction, to write the row the migration will find.
    await db_session.execute(text("ALTER TABLE plans ALTER COLUMN exam_code DROP NOT NULL"))
    await db_session.execute(
        text(
            "INSERT INTO plans (id, code, stripe_price_id, exam_code, amount_pence, duration_days) VALUES "
            "(gen_random_uuid(), 'vague', 'price_vague', NULL, 100, 30), "
            "(gen_random_uuid(), 'named', 'price_named', 'sca', 100, 30)"
        )
    )

    await db_session.execute(text(migration("fbe151cbbf1f").BACKFILL_SQL))
    await db_session.execute(text("ALTER TABLE plans ALTER COLUMN exam_code SET NOT NULL"))

    rows = (
        await db_session.execute(select(Plan.code, Plan.exam_code, Plan.active).order_by(Plan.code))
    ).all()
    assert [tuple(row) for row in rows] == [("named", "sca", True), ("vague", "", False)]

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await db_session.execute(
                text(
                    "INSERT INTO plans (id, code, stripe_price_id, amount_pence, duration_days) "
                    "VALUES (gen_random_uuid(), 'unnamed', 'price_unnamed', 100, 30)"
                )
            )


async def test_every_payment_without_a_receipt_is_given_one(db_session: AsyncSession) -> None:
    """B-4: an old payment gets a receipt id in the settlement's own format, naming
    the plan's exam, else the granted exam, else `all`; one it already has is kept."""
    import re
    from datetime import UTC, datetime

    from app.features.billing import repository as billing_repo
    from app.features.billing.models import Payment
    from app.features.entitlements import repository as entitlements_repo
    from app.features.identity import repository as identity_repo
    from tests.support.catalog import ensure_exam

    buyer = await identity_repo.create_user(
        session=db_session, email="old-buyer@example.com", name="Old Buyer", password_hash=None
    )
    plab = await ensure_exam(db_session, "plab")
    plan = await billing_repo.create_plan(
        db_session,
        code="sca_1m",
        stripe_price_id="price_old",
        amount_pence=2499,
        duration_days=30,
        exam_code="sca",
    )
    grant = await entitlements_repo.grant(
        session=db_session, user_id=buyer.id, exam_id=plab.id, source="purchase"
    )
    paid_at = datetime(2025, 1, 1, tzinfo=UTC)
    payments = [
        Payment(
            user_id=buyer.id,
            plan_id=plan.id,
            stripe_payment_intent_id="pi_plan",
            amount_total_pence=2499,
            currency="gbp",
            paid_at=paid_at,
        ),
        Payment(
            user_id=buyer.id,
            entitlement_id=grant.id,
            stripe_payment_intent_id="pi_grant",
            amount_total_pence=2499,
            currency="gbp",
            paid_at=paid_at,
        ),
        Payment(
            user_id=buyer.id,
            stripe_payment_intent_id="pi_bare",
            amount_total_pence=2499,
            currency="gbp",
            paid_at=paid_at,
        ),
        Payment(
            user_id=buyer.id,
            receipt_id="RCP-sca-kept0000",
            stripe_payment_intent_id="pi_kept",
            amount_total_pence=2499,
            currency="gbp",
            paid_at=paid_at,
        ),
    ]
    db_session.add_all(payments)
    await db_session.flush()

    written = await db_session.run_sync(
        lambda sync_session: migration("e27eb81413ee").backfill(sync_session.connection())
    )

    assert written == 3
    receipts = dict(
        (await db_session.execute(select(Payment.stripe_payment_intent_id, Payment.receipt_id))).all()
    )
    assert re.fullmatch(r"RCP-sca-[0-9a-f]{8}", receipts["pi_plan"])
    assert re.fullmatch(r"RCP-plab-[0-9a-f]{8}", receipts["pi_grant"])
    assert re.fullmatch(r"RCP-all-[0-9a-f]{8}", receipts["pi_bare"])
    assert receipts["pi_kept"] == "RCP-sca-kept0000"
    assert (
        await db_session.run_sync(
            lambda sync_session: migration("e27eb81413ee").backfill(sync_session.connection())
        )
        == 0
    ), "a second run finds nothing left to mint"
