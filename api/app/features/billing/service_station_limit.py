"""How many library stations a person's paid plans unlock, and whether a bigger plan exists.

Only a live purchase ever limits the library (ADR 0012: entitlement is not payment, and a
non-purchase grant such as an org grant or the free trial carries no plan to read a limit
from). When a purchase and some other live grant overlap, the purchase's limit is not trusted
either, because the other grant may already be covering the whole library.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import domain, repository
from app.features.billing.models import Plan
from app.features.entitlements import service as entitlements


async def station_limit_for(
    session: AsyncSession, *, user_id: uuid.UUID, exam_id: uuid.UUID, exam_code: str, now: datetime
) -> int | None:
    """How many library stations this person's paid plans unlock for the exam. `None` means no
    limit: either they hold no live purchase, or some other live grant (org, SSO tenant, admin,
    trial) overlaps it, which this slice never caps."""
    running = await entitlements.running_purchases(session, user_id, exam_code, now=now)
    if not running:
        return None

    # A purchase alongside any other live grant for this exam is not capped: the other grant
    # may already unlock everything, and this slice has no way to tell from here.
    all_grants = await entitlements.list_for_user(session, user_id, now=now)
    other_live_grants = [
        grant
        for grant in all_grants
        if grant.live and grant.exam_code == exam_code and grant.source != "purchase"
    ]
    if other_live_grants:
        return None

    running_ids = {grant.id for grant in running}
    plans_by_id = {plan.id: plan for plan in await repository.all_plans(session)}
    plans_by_code = {plan.code: plan for plan in plans_by_id.values()}
    matched_plans: list[Plan] = []
    for payment in await repository.payments_for_user(session, user_id):
        if payment.entitlement_id not in running_ids or payment.plan_id is None:
            continue
        plan = plans_by_id.get(payment.plan_id)
        if plan is None:
            # A live purchase grant with no matching plan row: nothing to read a limit from, so
            # the safe answer is "no limit" rather than silently ignoring this grant.
            return None
        base_code = plan.code.removesuffix(domain.REFERRAL_PLAN_SUFFIX)
        base_plan = plans_by_code.get(base_code, plan)
        matched_plans.append(base_plan)

    if not matched_plans:
        # Every live purchase grant matched no payment/plan row at all.
        return None
    if any(plan.station_limit is None for plan in matched_plans):
        return None
    return max(plan.station_limit for plan in matched_plans if plan.station_limit is not None)


async def can_upgrade(
    session: AsyncSession, *, user_id: uuid.UUID, exam_id: uuid.UUID, exam_code: str, now: datetime
) -> bool:
    """Whether a bigger plan than the one this person holds is on sale for the exam.

    Someone with no live paid access (a live grant whose source is not the free trial, a purchase
    or an org grant alike) always can, because there is nothing yet to compare against; someone
    whose current access already has no limit cannot, because nothing is bigger than "everything".
    """
    all_grants = await entitlements.list_for_user(session, user_id, now=now)
    has_paid_access = any(
        grant.live and grant.exam_code == exam_code and grant.source != "trial" for grant in all_grants
    )
    if not has_paid_access:
        return True
    limit = await station_limit_for(session, user_id=user_id, exam_id=exam_id, exam_code=exam_code, now=now)
    if limit is None:
        return False
    plans = await repository.all_plans(session)
    return any(
        plan.exam_code == exam_code
        and plan.active
        and not domain.is_referral_plan(plan.code)
        and (plan.station_limit is None or plan.station_limit > limit)
        for plan in plans
    )
