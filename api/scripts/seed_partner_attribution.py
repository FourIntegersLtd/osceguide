"""Write the BMJ partner-attribution demo data into Postgres: arrivals,
signups, payments, the pilot's commercial config, and a reporter account.

    poetry run python scripts/seed_partner_attribution.py --dry-run
    poetry run python scripts/seed_partner_attribution.py

Requires `sca`, `plab` and `ortho` to already exist (`scripts/seed_platform.py`
first) — a pilot cannot attribute visits to an exam that is not there yet.

Idempotent by construction: every row this script writes is keyed off a
visitor's deterministic suffix (`vk_seed_dashboard_01`, `seed_dashboard_u_01@…`,
`pi_seed_dashboard_01`, …), so a second run finds each row already present and
changes nothing. There is no tag column anywhere in `growth` or `billing` —
the deterministic key names are what `--clean` (below) and a second run both
key off, in place of one.

`--clean` removes exactly the rows this script can have written — the seeded
users, their acquisitions and payments, and the seeded arrivals and reporter
grant — and leaves the exams' `partner_pilot` flag, the `Plan` rows and the
pilot's commercial config alone, since those are shared configuration a demo
teardown should not have to recreate.
"""

from __future__ import annotations

import argparse
import asyncio
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import get_session_factory, import_all_models  # noqa: E402
from app.features.billing import repository as billing_repository  # noqa: E402
from app.features.billing.models import Payment, Plan  # noqa: E402
from app.features.catalog import repository as catalog_repository  # noqa: E402
from app.features.catalog import service_authoring as catalog  # noqa: E402
from app.features.catalog.errors import UnknownExamError  # noqa: E402
from app.features.growth import domain  # noqa: E402
from app.features.growth import repository as growth_repository
from app.features.growth.models import Acquisition, PartnerArrival, PartnerReporter  # noqa: E402
from app.features.identity import repository as identity_repository  # noqa: E402
from app.features.identity.models import User  # noqa: E402
from app.features.identity.tokens import hash_password  # noqa: E402
from scripts.seed_partner_attribution_data import (  # noqa: E402
    SEED_KEY_PREFIX,
    SEED_PARTNER,
    SEED_REPORTER_EMAIL,
    VisitorSeed,
    build_visitors,
    seed_summary,
)

# Printed, never stored anywhere but the hash: the demo reporter's account
# needs a password an operator can actually hand to someone, and a fresh
# random one means nobody can find it by reading this file.
_REPORTER_PASSWORD_LENGTH = 20


class _Rollback(Exception):
    """Ends the seeding transaction without committing. Never escapes `seed`."""


async def _ensure_pilot_exams(session: AsyncSession) -> None:
    """Flip `partner_pilot` on for the three exams BMJ's pilot covers.

    Refuses loudly rather than silently seeding zero arrivals: an exam
    missing here means `scripts/seed_platform.py` has not been run, and every
    arrival this script writes would carry a null `exam_code`.
    """
    for code in ("sca", "plab", "ortho"):
        exam = await catalog_repository.exam_by_code(session, None, code)
        if exam is None:
            raise UnknownExamError(f"{code}: run scripts/seed_platform.py before seeding the BMJ demo")
        if not exam.partner_pilot:
            await catalog.update_exam(session, exam.id, org_id=None, partner_pilot=True)


async def _ensure_plan(session: AsyncSession, payment_seed) -> Plan:  # type: ignore[no-untyped-def]
    """The `Plan` row a seeded payment points at, creating it once per
    (exam, plan length) the demo data actually uses."""
    existing = await billing_repository.plan_by_code(session, payment_seed.plan_code)
    if existing is not None:
        return existing
    return await billing_repository.create_plan(
        session,
        code=payment_seed.plan_code,
        stripe_price_id=f"price_{SEED_KEY_PREFIX}_{payment_seed.plan_code}",
        amount_pence=payment_seed.amount_pence,
        duration_days=(payment_seed.plan_ends_at - payment_seed.paid_at).days,
        exam_code=payment_seed.exam_code,
    )


async def _ensure_reporter(session: AsyncSession) -> str | None:
    """Create the demo reporter account and grant, if neither exists yet.

    Returns the printed password on the run that creates the account, and
    `None` on every later run — there is nothing new to tell an operator once
    the account already exists, and re-hashing a fresh password every run
    would silently invalidate whatever password was printed the first time.
    """
    existing_user = await identity_repository.user_by_email(session, SEED_REPORTER_EMAIL)
    password: str | None = None
    if existing_user is None:
        password = secrets.token_urlsafe(_REPORTER_PASSWORD_LENGTH)
        await identity_repository.create_user(
            session,
            email=SEED_REPORTER_EMAIL,
            name="BMJ Reporter",
            password_hash=await hash_password(password),
        )
    if not await growth_repository.is_reporter(session, partner=SEED_PARTNER, email=SEED_REPORTER_EMAIL):
        await growth_repository.add_reporter(session, partner=SEED_PARTNER, email=SEED_REPORTER_EMAIL)
    return password


async def _ensure_pilot_config(session: AsyncSession) -> None:
    """BMJ's cost-per-click and spend-alert thresholds, so the dashboard's
    spend and margin figures read against real settings rather than only the
    code's own defaults.

    `last_alerted_threshold_pence` is set to the highest threshold up front,
    so loading the freshly seeded dashboard does not fire a spend alert for
    six months of backdated "spend" all landing in the same instant — the
    same reason the legacy fixture set it (`_pilot_config_document`).
    """
    if await growth_repository.pilot_config(session, SEED_PARTNER) is not None:
        return
    thresholds = list(domain.DEFAULT_SPEND_ALERT_THRESHOLDS_PENCE)
    await growth_repository.save_pilot_config(
        session,
        SEED_PARTNER,
        cost_per_click_pence=domain.DEFAULT_COST_PER_CLICK_PENCE,
        spend_alert_thresholds_pence=thresholds,
        spend_alert_recipients=[],
        last_alerted_threshold_pence=max(thresholds) if thresholds else 0,
    )


async def _seed_visitor(session: AsyncSession, visitor: VisitorSeed) -> bool:
    """Write one visitor's arrivals, signup and payments. Returns `False`
    (and writes nothing) if this visitor's key is already in the database —
    the idempotence a re-run and `--dry-run`-then-real-run both rely on."""
    if await growth_repository.latest_arrival_for_visitor(session, visitor.visitor_key) is not None:
        return False

    first_arrival_id = None
    for landed_at in visitor.arrival_times:
        # `repository.record_arrival` always stamps `landed_at` as "now" —
        # right for a live visit, wrong for six months of backdated demo
        # history — so this writes the row directly, the one place this
        # script reaches past the slice's own repository function.
        arrival = PartnerArrival(
            partner=SEED_PARTNER,
            exam_code=visitor.exam_code,
            visitor_key=visitor.visitor_key,
            ref_id=visitor.ref_id,
            landing_path=visitor.landing_path,
            utm={"utm_medium": "referral", "utm_campaign": visitor.campaign},
            landed_at=landed_at,
        )
        session.add(arrival)
        await session.flush()
        if first_arrival_id is None:
            first_arrival_id = arrival.id

    if visitor.signup is None:
        return True

    user = await identity_repository.create_user(
        session, email=visitor.signup.email, name=visitor.signup.name, password_hash=None
    )
    await growth_repository.record_acquisition(
        session,
        user_id=user.id,
        partner=SEED_PARTNER,
        exam_code=visitor.signup.exam_code,
        arrival_id=first_arrival_id,
        at=visitor.signup.acquired_at,
    )
    for payment_seed in visitor.signup.payments:
        plan = await _ensure_plan(session, payment_seed)
        await billing_repository.record_payment(
            session,
            user_id=user.id,
            plan_id=plan.id,
            stripe_payment_intent_id=payment_seed.stripe_payment_intent_id,
            checkout_session_id=payment_seed.checkout_session_id,
            amount_total_pence=payment_seed.amount_pence,
            currency="gbp",
            receipt_url=None,
            paid_at=payment_seed.paid_at,
            entitlement_id=None,
            receipt_id=payment_seed.receipt_id,
            customer_email=visitor.signup.email,
            customer_name=visitor.signup.name,
            plan_ends_at=payment_seed.plan_ends_at,
        )
    return True


async def _clean(session: AsyncSession) -> tuple[int, int, int, int]:
    """Remove every row a previous run of this script could have written,
    identified purely by the deterministic key prefixes above — never by a
    tag column, since none exists. Leaves `Plan` rows, the exams'
    `partner_pilot` flag and the pilot's commercial config untouched, since
    those are shared settings a teardown should not have to recreate."""
    seed_user_ids = list(
        (await session.execute(select(User.id).where(User.email.like(f"{SEED_KEY_PREFIX}_u_%")))).scalars()
    )
    payments_deleted = 0
    acquisitions_deleted = 0
    if seed_user_ids:
        payments_result = await session.execute(delete(Payment).where(Payment.user_id.in_(seed_user_ids)))
        payments_deleted = getattr(payments_result, "rowcount", 0) or 0
        acquisitions_result = await session.execute(
            delete(Acquisition).where(Acquisition.user_id.in_(seed_user_ids))
        )
        acquisitions_deleted = getattr(acquisitions_result, "rowcount", 0) or 0
        await session.execute(delete(User).where(User.id.in_(seed_user_ids)))
    arrivals_result = await session.execute(
        delete(PartnerArrival).where(PartnerArrival.visitor_key.like(f"vk_{SEED_KEY_PREFIX}_%"))
    )
    arrivals_deleted = getattr(arrivals_result, "rowcount", 0) or 0
    reporters_result = await session.execute(
        delete(PartnerReporter).where(
            PartnerReporter.partner == SEED_PARTNER, PartnerReporter.email == SEED_REPORTER_EMAIL
        )
    )
    reporters_deleted = getattr(reporters_result, "rowcount", 0) or 0
    await session.execute(delete(User).where(User.email == SEED_REPORTER_EMAIL))
    return len(seed_user_ids), payments_deleted + acquisitions_deleted, arrivals_deleted, reporters_deleted


async def seed(*, dry_run: bool, clean: bool) -> int:
    """Run the whole demo seed (or, with `clean`, tear it down) in one
    transaction, rolling back instead of committing when `dry_run` is set."""
    import_all_models()
    factory = get_session_factory()
    password: str | None = None
    written = 0
    skipped = 0
    try:
        async with factory() as session, session.begin():
            if clean:
                users, rows, arrivals, reporters = await _clean(session)
                print(  # noqa: T201
                    f"{'would remove' if dry_run else 'removed'}: "
                    f"{users} seeded users, {rows} payment/acquisition rows, "
                    f"{arrivals} arrivals, {reporters} reporter grants"
                )
            else:
                await _ensure_pilot_exams(session)
                await _ensure_pilot_config(session)
                password = await _ensure_reporter(session)
                visitors = build_visitors()
                for visitor in visitors:
                    if await _seed_visitor(session, visitor):
                        written += 1
                    else:
                        skipped += 1
                print(f"{'would write' if dry_run else 'wrote'}: {seed_summary(visitors)}")  # noqa: T201
                print(f"visitors written: {written}, already present: {skipped}")  # noqa: T201
                if password:
                    print(f"reporter account created: {SEED_REPORTER_EMAIL} / {password}")  # noqa: T201
                else:
                    print(f"reporter account already existed: {SEED_REPORTER_EMAIL}")  # noqa: T201

            if dry_run:
                raise _Rollback()
    except _Rollback:
        pass
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the seed (or clean) inside one asyncio event loop."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Roll back instead of committing.")
    parser.add_argument(
        "--clean", action="store_true", help="Remove previously seeded rows instead of writing new ones."
    )
    args = parser.parse_args(argv)
    return asyncio.run(seed(dry_run=args.dry_run, clean=args.clean))


if __name__ == "__main__":
    raise SystemExit(main())
