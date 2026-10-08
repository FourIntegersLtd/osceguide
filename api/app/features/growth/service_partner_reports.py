"""What a partner sees of their own pilot: visits, sign-ups and the fee they are owed.

No revenue and no margin, ever. These are the same counts the admin's
dashboard (`service_dashboard.py`) shows, with those figures left out, so a
partner can be given this view without being shown what the pilot earns.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import service as billing
from app.features.growth import domain, repository, service_dashboard, service_spend
from app.features.growth.schemas import (
    CountOverTimePoint,
    CountOverTimeReport,
    FeeOverTimePoint,
    FeeOverTimeReport,
    PartnerBreakdownRow,
    PartnerDashboardSummaryRead,
    PartnerFeeSummary,
)

# The breakdown table shows the ten busiest campaigns.
_CAMPAIGN_BREAKDOWN_LIMIT = 10


async def read_partner_summary(
    session: AsyncSession,
    *,
    partner: str,
    from_date: date,
    to_date: date,
    exam_code: str | None,
    utm_campaign: str | None,
) -> PartnerDashboardSummaryRead:
    """The partner-mode Overview tab: fee-framed, never revenue-framed.

    Oracle: b2c `_to_partner_summary` — the same underlying numbers as the
    admin summary, with every money figure but the partner's own fee removed.
    """
    partner_key = service_spend.organisation_partner(partner)
    service_spend.require_range(from_date, to_date)
    landed_from, landed_before = domain.ledger_bounds(from_date, to_date)

    raw_arrivals = await repository.count_arrivals_between(
        session,
        partner_key,
        landed_from=landed_from,
        landed_before=landed_before,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
    )
    unique_arrivals = await repository.unique_arrival_count(
        session,
        partner_key,
        landed_from=landed_from,
        landed_before=landed_before,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
    )
    acquired_ids = await service_dashboard.acquired_user_ids(
        session,
        partner_key,
        acquired_from=landed_from,
        acquired_before=landed_before,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
    )
    paying_ids = await billing.payer_user_ids_among(
        session, acquired_ids, paid_from=landed_from, paid_before=landed_before
    )

    config = await service_spend.read_config_for(session, partner_key=partner_key)
    estimate = domain.estimate_spend(
        arrivals=raw_arrivals,
        acquisitions=len(acquired_ids),
        gross_revenue_pence=0,
        cost_per_click_pence=config.cost_per_click_pence,
    )
    fee = PartnerFeeSummary(
        estimated_click_count=estimate.estimated_click_count,
        cost_per_click_pence=estimate.cost_per_click_pence,
        estimated_spend_pence=estimate.estimated_spend_pence,
    )

    by_exam, by_campaign = await _partner_breakdowns(
        session,
        partner_key,
        landed_from=landed_from,
        landed_before=landed_before,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
    )
    return PartnerDashboardSummaryRead(
        partner=partner_key,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
        from_date=from_date,
        to_date=to_date,
        raw_arrival_count=raw_arrivals,
        unique_arrival_count=unique_arrivals,
        acquired_user_count=len(acquired_ids),
        paying_user_count=len(paying_ids),
        fee=fee,
        breakdown_by_exam=by_exam,
        breakdown_by_campaign=by_campaign,
    )


async def _partner_breakdowns(
    session: AsyncSession,
    partner: str,
    *,
    landed_from: Any,
    landed_before: Any,
    exam_code: str | None,
    utm_campaign: str | None,
) -> tuple[list[PartnerBreakdownRow], list[PartnerBreakdownRow]]:
    """Visits, signups and payments per exam and per (top-10) campaign.

    Oracle: b2c `build_partner_breakdowns`. Arrivals and sign-ups are both
    narrowed by the exam and campaign filters; a dimension appears if it has
    a visit, a sign-up or a payer; exams sort by name, campaigns by visits
    (then name) and keep ten. Never any money: a partner's Performance tab
    reads counts only.
    """
    visits_by_exam = await repository.visits_by_exam(
        session,
        partner,
        landed_from=landed_from,
        landed_before=landed_before,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
    )
    visits_by_campaign = await repository.visits_by_campaign(
        session,
        partner,
        landed_from=landed_from,
        landed_before=landed_before,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
    )
    acquisitions = await repository.acquisitions_with_campaign(
        session,
        partner,
        acquired_from=landed_from,
        acquired_before=landed_before,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
    )
    acquired_user_ids = [user_id for user_id, _exam, _campaign in acquisitions]
    paying_ids = await billing.payer_user_ids_among(
        session, acquired_user_ids, paid_from=landed_from, paid_before=landed_before
    )

    signups_by_exam: dict[str, int] = {}
    paid_by_exam: dict[str, int] = {}
    signups_by_campaign: dict[str, int] = {}
    paid_by_campaign: dict[str, int] = {}
    for user_id, acquisition_exam, campaign in acquisitions:
        signups_by_exam[acquisition_exam] = signups_by_exam.get(acquisition_exam, 0) + 1
        signups_by_campaign[campaign] = signups_by_campaign.get(campaign, 0) + 1
        if user_id in paying_ids:
            paid_by_exam[acquisition_exam] = paid_by_exam.get(acquisition_exam, 0) + 1
            paid_by_campaign[campaign] = paid_by_campaign.get(campaign, 0) + 1

    by_exam = [
        PartnerBreakdownRow(
            dimension=dimension,
            visit_count=visits_by_exam.get(dimension, 0),
            signup_count=signups_by_exam.get(dimension, 0),
            paid_count=paid_by_exam.get(dimension, 0),
        )
        for dimension in sorted(set(visits_by_exam) | set(signups_by_exam) | set(paid_by_exam))
    ]
    campaign_keys = sorted(
        set(visits_by_campaign) | set(signups_by_campaign) | set(paid_by_campaign),
        key=lambda key: (-visits_by_campaign.get(key, 0), key),
    )[:_CAMPAIGN_BREAKDOWN_LIMIT]
    by_campaign = [
        PartnerBreakdownRow(
            dimension=dimension,
            visit_count=visits_by_campaign.get(dimension, 0),
            signup_count=signups_by_campaign.get(dimension, 0),
            paid_count=paid_by_campaign.get(dimension, 0),
        )
        for dimension in campaign_keys
    ]
    return by_exam, by_campaign


async def read_visits_over_time(
    session: AsyncSession,
    *,
    partner: str,
    from_date: date,
    to_date: date,
    exam_code: str | None,
    utm_campaign: str | None,
    bucket: str,
) -> CountOverTimeReport:
    """The partner Performance tab's visits chart."""
    partner_key = service_spend.organisation_partner(partner)
    service_spend.require_range(from_date, to_date)
    bucket_key = service_spend.require_bucket(bucket)
    landed_from, landed_before = domain.ledger_bounds(from_date, to_date)
    rows = await repository.arrivals_over_time(
        session,
        partner_key,
        landed_from=landed_from,
        landed_before=landed_before,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
        bucket=bucket_key,
    )
    by_period = {period.date(): count for period, count in rows}
    points = [
        CountOverTimePoint(period=period, count=by_period.get(period, 0))
        for period in domain.iter_bucket_starts(from_date, to_date, bucket_key)
    ]
    return CountOverTimeReport(
        partner=partner_key,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
        from_date=from_date,
        to_date=to_date,
        bucket=bucket_key,
        points=points,
    )


async def read_signups_over_time(
    session: AsyncSession,
    *,
    partner: str,
    from_date: date,
    to_date: date,
    exam_code: str | None,
    utm_campaign: str | None,
    bucket: str,
) -> CountOverTimeReport:
    """The partner Performance tab's signups chart."""
    partner_key = service_spend.organisation_partner(partner)
    service_spend.require_range(from_date, to_date)
    bucket_key = service_spend.require_bucket(bucket)
    acquired_from, acquired_before = domain.ledger_bounds(from_date, to_date)
    rows = await repository.acquisitions_over_time(
        session,
        partner_key,
        acquired_from=acquired_from,
        acquired_before=acquired_before,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
        bucket=bucket_key,
    )
    by_period = {period.date(): count for period, count in rows}
    points = [
        CountOverTimePoint(period=period, count=by_period.get(period, 0))
        for period in domain.iter_bucket_starts(from_date, to_date, bucket_key)
    ]
    return CountOverTimeReport(
        partner=partner_key,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
        from_date=from_date,
        to_date=to_date,
        bucket=bucket_key,
        points=points,
    )


async def read_fee_over_time(
    session: AsyncSession,
    *,
    partner: str,
    from_date: date,
    to_date: date,
    exam_code: str | None,
    utm_campaign: str | None,
    bucket: str,
) -> FeeOverTimeReport:
    """The partner "Your fee" tab's chart: visits and their estimated fee, per bucket."""
    partner_key = service_spend.organisation_partner(partner)
    service_spend.require_range(from_date, to_date)
    bucket_key = service_spend.require_bucket(bucket)
    landed_from, landed_before = domain.ledger_bounds(from_date, to_date)
    config = await service_spend.read_config_for(session, partner_key=partner_key)
    rows = await repository.arrivals_over_time(
        session,
        partner_key,
        landed_from=landed_from,
        landed_before=landed_before,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
        bucket=bucket_key,
    )
    by_period = {period.date(): count for period, count in rows}
    points = [
        FeeOverTimePoint(
            period=period,
            visit_count=by_period.get(period, 0),
            estimated_fee_pence=by_period.get(period, 0) * config.cost_per_click_pence,
        )
        for period in domain.iter_bucket_starts(from_date, to_date, bucket_key)
    ]
    return FeeOverTimeReport(
        partner=partner_key,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
        from_date=from_date,
        to_date=to_date,
        bucket=bucket_key,
        cost_per_click_pence=config.cost_per_click_pence,
        points=points,
    )
