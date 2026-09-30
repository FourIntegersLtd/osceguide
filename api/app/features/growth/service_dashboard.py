"""The BMJ dashboard: the admin's full view of a partner pilot, and the
partner-safe reporting view of the same numbers with every revenue and
margin figure removed.

Ported from b2c's `partner_dashboard_service`, `bmj_metrics_service`,
`bmj_anomaly_service`, `funnel_service` and `partner_reporting_service`. No
migration backs this: every figure here is computed on the fly from
`PartnerArrival`, `Acquisition`, `PartnerReporter` and `billing.payments`.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import EventCounts
from app.features.billing import service as billing
from app.features.catalog import service as catalog
from app.features.growth import domain, errors, repository, service_spend
from app.features.growth.schemas import (
    AcquiredRevenueReport,
    AcquiredUserRow,
    ArrivalRow,
    CountOverTimePoint,
    CountOverTimeReport,
    DashboardSummaryRead,
    FeeOverTimePoint,
    FeeOverTimeReport,
    LandingReconciliationRead,
    PartnerAnomaly,
    PartnerAnomalyReport,
    PartnerBreakdownRow,
    PartnerDashboardSummaryRead,
    PartnerFeeSummary,
    ReporterRead,
    RevenueByPlanRow,
    RevenueOverTimePoint,
    RevenueOverTimeReport,
)

# b2c's `CAMPAIGN_BREAKDOWN_LIMIT`: the breakdown table shows the ten busiest campaigns.
_CAMPAIGN_BREAKDOWN_LIMIT = 10


def _require_partner(partner: str) -> str:
    """The partner key, lower-cased, or `UnknownPartnerError` if it is not in the pilot."""
    partner_key = (partner or "").strip().lower()
    if partner_key not in domain.PILOT_PARTNERS:
        raise errors.UnknownPartnerError()
    return partner_key


def _require_range(from_date: date, to_date: date) -> None:
    """Refuse a range that ends before it begins."""
    try:
        domain.ensure_date_range(from_date, to_date)
    except domain.InvalidDateRange as error:
        raise errors.InvalidDateRangeError() from error


def _require_bucket(bucket: str) -> str:
    """The bucket name, or `InvalidInput` if it names none of day/week/month."""
    try:
        return domain.validate_bucket(bucket)
    except domain.InvalidBucket as error:
        raise errors.InvalidBucketError(str(error)) from error


async def _acquired_user_ids(
    session: AsyncSession,
    partner: str,
    *,
    acquired_from: Any,
    acquired_before: Any,
    exam_code: str | None,
    utm_campaign: str | None,
) -> list[uuid.UUID]:
    """This partner's acquisitions in a window, narrowed by exam and campaign as b2c does."""
    return await repository.acquired_user_ids_between(
        session,
        partner,
        acquired_from=acquired_from,
        acquired_before=acquired_before,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
    )


async def read_summary(
    session: AsyncSession,
    *,
    partner: str,
    from_date: date,
    to_date: date,
    exam_code: str | None,
    utm_campaign: str | None,
    event_counts: EventCounts,
) -> DashboardSummaryRead:
    """The admin Overview tab: every number the 5-tab dashboard's hero and
    anomaly panel need for one range, in a single call.

    Oracle: b2c `aggregate_dashboard_summary`. Reconciliation and spend are
    not reimplemented here — they already exist (G-1) and are reused as-is.
    """
    partner_key = _require_partner(partner)
    _require_range(from_date, to_date)
    if exam_code is not None:
        pilot_exams = await catalog.pilot_exam_codes(session)
        if exam_code not in pilot_exams:
            raise errors.ExamNotInPilotError()
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
    acquired_ids = await _acquired_user_ids(
        session,
        partner_key,
        acquired_from=landed_from,
        acquired_before=landed_before,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
    )

    reconciliation = await service_spend.reconcile_landings(
        session,
        partner=partner_key,
        from_date=from_date,
        to_date=to_date,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
        event_counts=event_counts,
    )
    revenue = await _revenue_report(
        session,
        partner=partner_key,
        from_date=from_date,
        to_date=to_date,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
        acquired_ids=acquired_ids,
    )
    spend = await service_spend.read_spend(session, partner=partner_key, from_date=from_date, to_date=to_date)
    anomalies = _anomaly_report(
        reconciliation=reconciliation,
        raw_arrival_count=raw_arrivals,
        signup_count=len(acquired_ids),
        purchase_count=revenue.paying_user_count,
        acquired_user_count=len(acquired_ids),
        net_margin_pence=spend.net_margin_pence,
    )
    return DashboardSummaryRead(
        partner=partner_key,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
        from_date=from_date,
        to_date=to_date,
        raw_arrival_count=raw_arrivals,
        unique_arrival_count=unique_arrivals,
        acquired_user_count=len(acquired_ids),
        reconciliation=reconciliation,
        revenue=revenue,
        spend=spend,
        anomalies=anomalies,
    )


def _anomaly_report(
    *,
    reconciliation: LandingReconciliationRead,
    raw_arrival_count: int,
    signup_count: int,
    purchase_count: int,
    acquired_user_count: int,
    net_margin_pence: int,
) -> PartnerAnomalyReport:
    """Turn `domain.detect_anomalies`'s pure result into the response shape."""
    found = domain.detect_anomalies(
        reconciliation_status=reconciliation.status,
        reconciliation_delta_percent=reconciliation.delta_percent,
        raw_arrival_count=raw_arrival_count,
        signup_count=signup_count,
        purchase_count=purchase_count,
        acquired_user_count=acquired_user_count,
        net_margin_pence=net_margin_pence,
    )
    items = [
        PartnerAnomaly(
            code=item.code,
            severity=item.severity,
            title=item.title,
            detail=item.detail,
            metric=item.metric,
        )
        for item in found
    ]
    return PartnerAnomalyReport(status="flagged" if items else "ok", count=len(items), items=items)


async def _revenue_report(
    session: AsyncSession,
    *,
    partner: str,
    from_date: date,
    to_date: date,
    exam_code: str | None,
    utm_campaign: str | None,
    acquired_ids: list[uuid.UUID],
) -> AcquiredRevenueReport:
    """What this partner's acquired users have paid in the range, by plan."""
    paid_from, paid_before = domain.ledger_bounds(from_date, to_date)
    breakdown = await billing.revenue_breakdown_for_users(
        session, acquired_ids, paid_from=paid_from, paid_before=paid_before
    )
    paying_ids = await billing.payer_user_ids_among(
        session, acquired_ids, paid_from=paid_from, paid_before=paid_before
    )
    rows = [
        RevenueByPlanRow(plan_type=plan_code or "unknown", payment_count=count, gross_revenue_pence=gross)
        for plan_code, count, gross in breakdown
    ]
    return AcquiredRevenueReport(
        partner=partner,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
        from_date=from_date,
        to_date=to_date,
        acquired_user_count=len(acquired_ids),
        paying_user_count=len(paying_ids),
        payment_count=sum(row.payment_count for row in rows),
        gross_revenue_pence=sum(row.gross_revenue_pence for row in rows),
        revenue_by_plan=rows,
    )


async def read_revenue(
    session: AsyncSession,
    *,
    partner: str,
    from_date: date,
    to_date: date,
    exam_code: str | None,
    utm_campaign: str | None,
) -> AcquiredRevenueReport:
    """The admin Revenue tab's headline numbers, standalone from the full summary."""
    partner_key = _require_partner(partner)
    _require_range(from_date, to_date)
    landed_from, landed_before = domain.ledger_bounds(from_date, to_date)
    acquired_ids = await _acquired_user_ids(
        session,
        partner_key,
        acquired_from=landed_from,
        acquired_before=landed_before,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
    )
    return await _revenue_report(
        session,
        partner=partner_key,
        from_date=from_date,
        to_date=to_date,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
        acquired_ids=acquired_ids,
    )


async def read_revenue_over_time(
    session: AsyncSession,
    *,
    partner: str,
    from_date: date,
    to_date: date,
    exam_code: str | None,
    utm_campaign: str | None,
    bucket: str,
) -> RevenueOverTimeReport:
    """The admin Revenue tab's chart: gross revenue per bucket, gaps filled with zero."""
    partner_key = _require_partner(partner)
    _require_range(from_date, to_date)
    bucket_key = _require_bucket(bucket)
    landed_from, landed_before = domain.ledger_bounds(from_date, to_date)
    acquired_ids = await _acquired_user_ids(
        session,
        partner_key,
        acquired_from=landed_from,
        acquired_before=landed_before,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
    )
    rows = await billing.revenue_over_time_for_users(
        session, acquired_ids, paid_from=landed_from, paid_before=landed_before, bucket=bucket_key
    )
    by_period = {period.date(): (count, gross) for period, count, gross in rows}
    points = [
        RevenueOverTimePoint(
            period=period,
            payment_count=by_period.get(period, (0, 0))[0],
            gross_revenue_pence=by_period.get(period, (0, 0))[1],
        )
        for period in domain.iter_bucket_starts(from_date, to_date, bucket_key)
    ]
    return RevenueOverTimeReport(
        partner=partner_key,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
        from_date=from_date,
        to_date=to_date,
        bucket=bucket_key,
        points=points,
    )


async def list_arrivals(
    session: AsyncSession,
    *,
    partner: str,
    from_date: date,
    to_date: date,
    exam_code: str | None,
    utm_campaign: str | None,
    search: str | None,
    limit: int,
    cursor: dict[str, Any] | None,
) -> tuple[list[ArrivalRow], str | None]:
    """The admin "recent activity" arrivals table, paginated and searchable."""
    partner_key = _require_partner(partner)
    _require_range(from_date, to_date)
    landed_from, landed_before = domain.ledger_bounds(from_date, to_date)
    arrivals, next_cursor = await repository.arrivals_page(
        session,
        partner_key,
        landed_from=landed_from,
        landed_before=landed_before,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
        search=search,
        limit=limit,
        cursor=cursor,
    )
    rows = [
        ArrivalRow(
            arrival_id=arrival.id,
            partner=arrival.partner,
            exam_code=arrival.exam_code,
            utm_medium=(arrival.utm or {}).get("utm_medium"),
            utm_campaign=(arrival.utm or {}).get("utm_campaign"),
            landing_path=arrival.landing_path,
            visitor_key=arrival.visitor_key,
            landed_at=arrival.landed_at,
        )
        for arrival in arrivals
    ]
    return rows, next_cursor


async def list_acquired_users(
    session: AsyncSession,
    *,
    partner: str,
    from_date: date,
    to_date: date,
    exam_code: str | None,
    utm_campaign: str | None,
    limit: int,
    cursor: dict[str, Any] | None,
) -> tuple[list[AcquiredUserRow], str | None]:
    """The admin "recent activity" acquired-users table, paginated.

    Each row is enriched with its originating arrival's UTM tags, so the table
    reads like the legacy one without `Acquisition` itself carrying them.
    """
    partner_key = _require_partner(partner)
    _require_range(from_date, to_date)
    acquired_from, acquired_before = domain.ledger_bounds(from_date, to_date)
    acquisitions, next_cursor = await repository.acquired_users_page(
        session,
        partner_key,
        acquired_from=acquired_from,
        acquired_before=acquired_before,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
        limit=limit,
        cursor=cursor,
    )
    arrival_ids = [row.arrival_id for row in acquisitions if row.arrival_id is not None]
    arrivals_by_id = await repository.arrivals_by_ids(session, arrival_ids)
    rows = []
    for acquisition in acquisitions:
        arrival = arrivals_by_id.get(acquisition.arrival_id) if acquisition.arrival_id else None
        utm = (arrival.utm if arrival else None) or {}
        rows.append(
            AcquiredUserRow(
                user_id=acquisition.user_id,
                exam_code=acquisition.exam_code,
                utm_medium=utm.get("utm_medium"),
                utm_campaign=utm.get("utm_campaign"),
                original_ref_id=arrival.ref_id if arrival else None,
                acquired_at=acquisition.acquired_at,
                visitor_key=arrival.visitor_key if arrival else None,
            )
        )
    return rows, next_cursor


async def list_reporters(session: AsyncSession, *, partner: str) -> list[ReporterRead]:
    """The admin Access tab's reporter list, active and revoked alike."""
    partner_key = _require_partner(partner)
    reporters = await repository.reporters_for_partner(session, partner_key)
    return [
        ReporterRead(
            email=reporter.email,
            partner=reporter.partner,
            created_at=reporter.created_at,
            revoked_at=reporter.revoked_at,
        )
        for reporter in reporters
    ]


async def revoke_reporter(session: AsyncSession, *, partner: str, email: str) -> None:
    """Take away a reporter's access. Raises `ReporterNotFound` if there was
    no live grant to revoke — deleting twice must not look like it worked twice."""
    partner_key = _require_partner(partner)
    revoked = await repository.revoke_reporter(session, partner=partner_key, email=email.strip().lower())
    if not revoked:
        raise errors.ReporterNotFound()


# --- partner-mode reporting (no revenue, ever) -------------------------------


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
    partner_key = _require_partner(partner)
    _require_range(from_date, to_date)
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
    acquired_ids = await _acquired_user_ids(
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

    config = await service_spend.read_config(session, partner=partner_key)
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
    partner_key = _require_partner(partner)
    _require_range(from_date, to_date)
    bucket_key = _require_bucket(bucket)
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
    partner_key = _require_partner(partner)
    _require_range(from_date, to_date)
    bucket_key = _require_bucket(bucket)
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
    partner_key = _require_partner(partner)
    _require_range(from_date, to_date)
    bucket_key = _require_bucket(bucket)
    landed_from, landed_before = domain.ledger_bounds(from_date, to_date)
    config = await service_spend.read_config(session, partner=partner_key)
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
