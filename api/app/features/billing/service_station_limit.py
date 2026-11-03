"""How many library stations a person's paid plans unlock, and whether a bigger plan exists.

Only a live purchase ever limits the library (ADR 0012: entitlement is not payment, and a
non-purchase grant such as an org grant or the free trial carries no plan to read a limit
from). When a purchase and some other live grant overlap, the purchase's limit is not trusted
either, because the other grant may already be covering the whole library.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import domain, repository
from app.features.billing.models import Plan
from app.features.entitlements import service as entitlements

logger = logging.getLogger(__name__)


def _strictest_limit(plans: list[Plan], exam_code: str) -> int | None:
    """The smallest station limit among the exam's active plans; `None` when none of them is capped.

    What a live purchase that matches no plan is held to, so an unlinked purchase can never again
    quietly unlock the whole library.
    """
    limits = [
        plan.station_limit
        for plan in plans
        if plan.exam_code == exam_code and plan.active and plan.station_limit is not None
    ]
    return min(limits) if limits else None


async def station_limit_for(
    session: AsyncSession, *, user_id: uuid.UUID, exam_id: uuid.UUID, exam_code: str, now: datetime
) -> int | None:
    """How many library stations this person's paid plans unlock for the exam. `None` means no
    limit: either they hold no live purchase, or some other live grant (org, SSO tenant, admin,
    trial) overlaps it, which this slice never caps."""
    limit, _ = await station_limit_and_plan_code(
        session, user_id=user_id, exam_code=exam_code, now=now, started_only=False
    )
    return limit


async def station_limit_and_plan_code(
    session: AsyncSession, *, user_id: uuid.UUID, exam_code: str, now: datetime, started_only: bool
) -> tuple[int | None, str | None]:
    """The limit `station_limit_for` gives, and the base plan code of the purchase that set it.

    The code is `None` when no purchase decides (none running, or another live grant overlaps),
    `"unknown"` when a running purchase matches no plan (the limit then fails closed), and
    otherwise the plan with the highest limit, or the first uncapped one when any plan is uncapped.
    `started_only` ignores purchases bought to start later, so a queued plan never names the reason.
    """
    running = await entitlements.running_purchases(session, user_id, exam_code, now=now)
    if started_only:
        running = [grant for grant in running if grant.starts_at <= now]
    if not running:
        return None, None

    # A purchase alongside any other live grant for this exam is not capped: the other grant
    # may already unlock everything, and this slice has no way to tell from here.
    all_grants = await entitlements.list_for_user(session, user_id, now=now)
    other_live_grants = [
        grant
        for grant in all_grants
        if grant.live and grant.exam_code == exam_code and grant.source != "purchase"
    ]
    if other_live_grants:
        return None, None

    running_ids = {grant.id for grant in running}
    plans_by_id = {plan.id: plan for plan in await repository.all_plans(session)}
    plans_by_code = {plan.code: plan for plan in plans_by_id.values()}
    matched_plans: list[Plan] = []
    for payment in await repository.payments_for_user(session, user_id):
        if payment.entitlement_id not in running_ids or payment.plan_id is None:
            continue
        plan = plans_by_id.get(payment.plan_id)
        if plan is None:
            # A live purchase grant whose plan row is gone: fail closed, not open.
            logger.warning("purchase of a missing plan for user %s, exam %s", user_id, exam_code)
            return _strictest_limit(list(plans_by_id.values()), exam_code), "unknown"
        base_code = plan.code.removesuffix(domain.REFERRAL_PLAN_SUFFIX)
        base_plan = plans_by_code.get(base_code, plan)
        matched_plans.append(base_plan)

    if not matched_plans:
        # Every live purchase grant matched no payment/plan row at all: fail closed, not open.
        logger.warning("live purchase with no linked plan for user %s, exam %s", user_id, exam_code)
        return _strictest_limit(list(plans_by_id.values()), exam_code), "unknown"
    for plan in matched_plans:
        if plan.station_limit is None:
            return None, plan.code
    deciding = max(matched_plans, key=lambda plan: plan.station_limit or 0)
    return deciding.station_limit, deciding.code


async def can_upgrade(
    session: AsyncSession, *, user_id: uuid.UUID, exam_id: uuid.UUID, exam_code: str, now: datetime
) -> bool:
    """Whether to offer "Upgrade to Pro" for the exam: only to someone with no paid access at all.

    Anyone holding a live grant that is not the free trial (a purchase of any length, an org grant)
    is never offered it, so a one-month subscriber is not pitched a plan they already have. Someone
    on the trial, or with nothing, is.
    """
    all_grants = await entitlements.list_for_user(session, user_id, now=now)
    has_paid_access = any(
        grant.live and grant.exam_code == exam_code and grant.source != "trial" for grant in all_grants
    )
    return not has_paid_access
