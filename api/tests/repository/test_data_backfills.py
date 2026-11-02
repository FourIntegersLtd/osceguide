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


async def test_b2c_never_doctor_accounts_are_flagged_and_matched_as_patient(db_session: AsyncSession) -> None:
    """P-2: the three addresses b2c hardcoded get `never_doctor`, whether or not
    they have practised yet, and the matcher then never makes them doctor."""
    from app.features.identity import repository as identity_repo
    from app.features.peer_practice import service_lifecycle
    from app.features.peer_practice.models import PracticeHistory

    practised = await identity_repo.create_user(
        session=db_session, email="Y.HKehinde@yahoo.com", name="Practised", password_hash=None
    )
    newcomer = await identity_repo.create_user(
        session=db_session, email="sheinat03@gmail.com", name="Newcomer", password_hash=None
    )
    bystander = await identity_repo.create_user(
        session=db_session, email="someone-else@example.com", name="Bystander", password_hash=None
    )
    db_session.add_all(
        [
            PracticeHistory(user_id=practised.id, last_role="patient", session_count=3),
            PracticeHistory(user_id=bystander.id, last_role="patient", session_count=3),
        ]
    )
    await db_session.flush()

    await db_session.execute(text(migration("39cc97f742b6").BACKFILL_SQL))

    stored = {
        user_id: (last_role, session_count, never_doctor)
        for user_id, last_role, session_count, never_doctor in (
            await db_session.execute(
                select(
                    PracticeHistory.user_id,
                    PracticeHistory.last_role,
                    PracticeHistory.session_count,
                    PracticeHistory.never_doctor,
                ).where(PracticeHistory.user_id.in_([practised.id, newcomer.id, bystander.id]))
            )
        ).all()
    }
    assert stored[practised.id] == ("patient", 3, True), "an existing history keeps its role and count"
    assert stored[newcomer.id] == (None, 0, True), "a newcomer is given a history carrying the flag"
    assert stored[bystander.id] == ("patient", 3, False)

    # What the matcher now decides, read through the service that pairs a
    # booking: both last played patient, so without the flag the practised
    # account, as the booking's owner, would be made doctor.
    doctor, patient = await service_lifecycle.roles_for_peer_participants(
        db_session, practised.id, bystander.id
    )
    assert (doctor, patient) == (bystander.id, practised.id)


async def test_the_approved_backfill_grandfathers_only_already_published_stations(
    db_session: AsyncSession,
) -> None:
    """The migration that added `stations.approved` ran this against every pre-existing row, so
    whatever was already live stayed visible; a draft or archived station is left unapproved,
    same as a station that becomes published after this shipped."""
    from app.features.stations.models import Station
    from tests.support.catalog import ensure_exam

    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    stations = {
        "published": Station(
            owner_kind="platform", org_id=None, exam_id=exam.id, title="Live", status="published"
        ),
        "draft": Station(owner_kind="platform", org_id=None, exam_id=exam.id, title="Draft", status="draft"),
        "archived": Station(
            owner_kind="platform", org_id=None, exam_id=exam.id, title="Old", status="archived"
        ),
    }
    db_session.add_all(stations.values())
    await db_session.flush()
    # Freshly inserted rows already default to false (the column's server default); the
    # migration's job is to flip the published one, which this proves by running its own SQL.
    assert {key: station.approved for key, station in stations.items()} == {
        "published": False,
        "draft": False,
        "archived": False,
    }

    await db_session.execute(text(migration("7b2f6a1d4e9c").BACKFILL_SQL))

    stored = dict(
        (
            await db_session.execute(
                select(Station.title, Station.approved).where(
                    Station.id.in_([station.id for station in stations.values()])
                )
            )
        ).all()
    )
    assert stored == {"Live": True, "Draft": False, "Old": False}


async def test_a_new_station_defaults_to_unapproved(db_session: AsyncSession) -> None:
    """Grandfathering is a one-time migration concern, not the model's default: a row created
    today, even a published one, starts out unapproved until an editor signs off on it."""
    from app.features.stations.models import Station
    from tests.support.catalog import ensure_exam

    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    station = Station(owner_kind="platform", org_id=None, exam_id=exam.id, title="New", status="published")
    db_session.add(station)
    await db_session.flush()

    assert station.approved is False
