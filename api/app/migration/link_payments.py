"""Tie each imported payment to the access it bought.

A payment is connected to its access only through `Payment.entitlement_id`. The live checkout
sets it; the legacy importers created the payment and the grant separately and never did. Without
the link a buyer is never capped to their plan's stations, can buy the same plan twice, and a
refund does not remove their access.

This is the one place that link is made, for both importers and for the repair script. It
never guesses: a payment with no single matching grant is reported and left alone.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing.models import Payment, Plan
from app.features.catalog.models import Exam
from app.features.entitlements.models import Entitlement

# A payment and the grant it bought start on the same day; a day either side absorbs time zones.
MATCH_WINDOW = timedelta(days=1)
# A grant's length can differ from the plan's duration by a few days (30 versus 31 day months).
PLAN_LENGTH_TOLERANCE_DAYS = 3


@dataclass
class LinkReport:
    """What one linking pass did."""

    linked: int = 0
    plans_filled: int = 0
    # One line per payment left alone, naming the payment and why.
    unresolved: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _Grant:
    """A purchase grant and the exam it is for."""

    entitlement: Entitlement
    exam_code: str


def _plan_for_grant(grant: _Grant, plans: Collection[Plan]) -> Plan | None:
    """The one standard plan of the grant's exam whose duration is closest to the grant's length, if unique.

    Referral twin plans share a duration and a station limit with their base plan; with the amount
    unknown, the base plan is the right default, so the twins are left out.
    """
    entitlement = grant.entitlement
    if entitlement.ends_at is None:
        return None
    length_days = (entitlement.ends_at - entitlement.starts_at).days
    candidates = sorted(
        (
            (abs(plan.duration_days - length_days), plan)
            for plan in plans
            if plan.exam_code == grant.exam_code and plan.active and not plan.code.endswith("_referral")
        ),
        key=lambda pair: pair[0],
    )
    if not candidates or candidates[0][0] > PLAN_LENGTH_TOLERANCE_DAYS:
        return None
    if len(candidates) > 1 and candidates[1][0] == candidates[0][0]:
        return None  # two plans equally close: do not guess
    return candidates[0][1]


def _matching_grant(
    payment: Payment, grants: list[_Grant], plans_by_id: dict[uuid.UUID, Plan]
) -> _Grant | None:
    """The single free grant this payment bought, or None when none or several fit."""
    plan = plans_by_id.get(payment.plan_id) if payment.plan_id else None
    candidates = [grant for grant in grants if plan is None or grant.exam_code == plan.exam_code]
    near = [
        grant for grant in candidates if abs(grant.entitlement.starts_at - payment.paid_at) <= MATCH_WINDOW
    ]
    if len(near) == 1:
        return near[0]
    if len(near) > 1:
        ranked = sorted(near, key=lambda grant: abs(grant.entitlement.starts_at - payment.paid_at))
        gap_first = abs(ranked[0].entitlement.starts_at - payment.paid_at)
        gap_second = abs(ranked[1].entitlement.starts_at - payment.paid_at)
        return ranked[0] if gap_first < gap_second else None
    return None


async def link_legacy_payments(
    session: AsyncSession, *, user_ids: Collection[uuid.UUID] | None = None
) -> LinkReport:
    """Link every unlinked payment (of these users, or all) to its purchase grant, and fill a missing plan.

    A payment links to the user's purchase grant starting within a day of `paid_at`, for the same
    exam as its plan when it has one. Each grant is used by one payment. A payment with no plan
    gets the plan whose duration matches its grant. Anything ambiguous goes in `unresolved`.
    Only flushes: the caller commits or rolls back (a dry run rolls back).
    """
    report = LinkReport()
    statement = select(Payment).where(Payment.entitlement_id.is_(None))
    if user_ids is not None:
        statement = statement.where(Payment.user_id.in_(list(user_ids)))
    unlinked = list((await session.execute(statement.order_by(Payment.paid_at))).scalars())
    if not unlinked:
        return report

    plans = list((await session.scalars(select(Plan))).all())
    plans_by_id = {plan.id: plan for plan in plans}
    user_set = {payment.user_id for payment in unlinked}
    already_linked = set(
        (
            await session.scalars(
                select(Payment.entitlement_id).where(
                    Payment.user_id.in_(user_set), Payment.entitlement_id.is_not(None)
                )
            )
        ).all()
    )
    grants_by_user: dict[uuid.UUID, list[_Grant]] = defaultdict(list)
    grant_rows = await session.execute(
        select(Entitlement, Exam.code)
        .join(Exam, Exam.id == Entitlement.exam_id)
        .where(Entitlement.user_id.in_(user_set), Entitlement.source == "purchase")
    )
    for entitlement, exam_code in grant_rows.all():
        if entitlement.id not in already_linked:
            grants_by_user[entitlement.user_id].append(_Grant(entitlement, str(exam_code)))

    for payment in unlinked:
        label = f"payment {payment.stripe_payment_intent_id} (user {payment.user_id})"
        free_grants = grants_by_user.get(payment.user_id, [])
        grant = _matching_grant(payment, free_grants, plans_by_id)
        if grant is None:
            report.unresolved.append(
                f"{label}: no single purchase grant starts within a day of {payment.paid_at}"
            )
            continue
        payment.entitlement_id = grant.entitlement.id
        free_grants.remove(grant)
        report.linked += 1
        if payment.plan_id is None:
            plan = _plan_for_grant(grant, plans)
            if plan is None:
                report.unresolved.append(f"{label}: linked, but no single plan fits the grant's length")
            else:
                payment.plan_id = plan.id
                report.plans_filled += 1
    await session.flush()
    return report
