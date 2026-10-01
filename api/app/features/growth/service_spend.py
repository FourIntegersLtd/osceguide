"""A partner pilot's money: our arrival ledger checked against Mixpanel, the estimated
spend on its clicks, and the email when that estimate crosses a threshold (G-1).

Ported from b2c's `reconciliation_service`, `partner_spend_service`,
`partner_pilot_config_service` and `partner_spend_alert_service`. The ledger in
this database is what a partner is paid on; Mixpanel is only a second opinion, so
Mixpanel being absent or down is a status on the report, never a refusal.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.ports import EventCounts, EventCountsFailed, EventCountsUnavailable
from app.core.settings import SettingsDep, get_settings
from app.features.billing import service as billing
from app.features.growth import domain, errors, repository
from app.features.growth.schemas import (
    LandingReconciliationRead,
    PartnerSpendRead,
    PilotConfigRead,
    UpdatePilotConfig,
)
from app.features.notifications import service as notifications

log = get_logger(__name__)

SPEND_ALERT_TEMPLATE = "partner_spend_alert"


def get_event_counts(settings: SettingsDep) -> EventCounts:
    """The Mixpanel adapter this deployment allows, as a route dependency. Overridden in tests."""
    from app.features.growth.mixpanel import build_event_counts

    return build_event_counts(settings)


async def reconcile_landings(
    session: AsyncSession,
    *,
    partner: str,
    from_date: date,
    to_date: date,
    exam_code: str | None,
    utm_campaign: str | None,
    event_counts: EventCounts,
) -> LandingReconciliationRead:
    """Our raw arrivals beside Mixpanel's `partner_referral_landing` count for the same range.

    Oracle: b2c `reconcile_landing_counts`. The two should roughly agree; a gap
    is something to look at, not something this decides about.
    """
    partner_key = require_partner(partner)
    require_range(from_date, to_date)
    landed_from, landed_before = domain.ledger_bounds(from_date, to_date)
    ledger_count = await repository.count_arrivals_between(
        session,
        partner_key,
        landed_from=landed_from,
        landed_before=landed_before,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
    )
    report = LandingReconciliationRead(
        partner=partner_key,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
        from_date=from_date,
        to_date=to_date,
        ledger_raw_count=ledger_count,
        status="ok",
    )
    where = {"partner": partner_key}
    if exam_code is not None:
        # platform-web sends the exam under `exam`, as the b2c client did.
        where["exam"] = exam_code
    if utm_campaign is not None:
        where["utm_campaign"] = utm_campaign
    try:
        mixpanel_count = await event_counts.count(
            event=domain.PARTNER_LANDING_EVENT, from_date=from_date, to_date=to_date, where=where
        )
    except EventCountsUnavailable as reason:
        return report.model_copy(update={"status": "mixpanel_unconfigured", "mixpanel_error": str(reason)})
    except EventCountsFailed as reason:
        return report.model_copy(update={"status": "mixpanel_error", "mixpanel_error": str(reason)})
    reconciled = domain.reconcile(ledger_count=ledger_count, analytics_count=mixpanel_count)
    return report.model_copy(
        update={
            "mixpanel_raw_count": mixpanel_count,
            "delta": reconciled.delta,
            "delta_percent": reconciled.delta_percent,
        }
    )


async def read_spend(
    session: AsyncSession, *, partner: str, from_date: date, to_date: date
) -> PartnerSpendRead:
    """Estimated spend on this partner's clicks in a range, against what the people
    it sent in that range paid. A read: judging the alert thresholds is the job's."""
    partner_key = require_partner(partner)
    require_range(from_date, to_date)
    config = await read_config(session, partner=partner_key)
    return await _spend(
        session, partner_key, from_date, to_date, cost_per_click_pence=config.cost_per_click_pence
    )


async def read_config(session: AsyncSession, *, partner: str) -> PilotConfigRead:
    """This partner's pilot settings, or b2c's defaults if nobody has saved any."""
    partner_key = require_partner(partner)
    stored = await repository.pilot_config(session, partner_key)
    if stored is None:
        return PilotConfigRead(
            partner=partner_key,
            cost_per_click_pence=domain.DEFAULT_COST_PER_CLICK_PENCE,
            spend_alert_thresholds_pence=list(domain.DEFAULT_SPEND_ALERT_THRESHOLDS_PENCE),
            spend_alert_recipients=[],
            last_alerted_threshold_pence=0,
        )
    return PilotConfigRead(
        partner=stored.partner,
        cost_per_click_pence=stored.cost_per_click_pence,
        spend_alert_thresholds_pence=list(stored.spend_alert_thresholds_pence),
        spend_alert_recipients=list(stored.spend_alert_recipients),
        last_alerted_threshold_pence=stored.last_alerted_threshold_pence,
    )


async def update_config(
    session: AsyncSession, *, partner: str, changes: UpdatePilotConfig
) -> PilotConfigRead:
    """Change a pilot's rate, thresholds or recipients; only what was sent changes.

    Oracle: b2c `update_partner_pilot_config`. Thresholds are kept distinct and
    ascending, recipients lower-cased.
    """
    current = await read_config(session, partner=partner)
    thresholds = (
        domain.normalise_thresholds(changes.spend_alert_thresholds_pence)
        if changes.spend_alert_thresholds_pence is not None
        else current.spend_alert_thresholds_pence
    )
    recipients = (
        [str(recipient).strip().lower() for recipient in changes.spend_alert_recipients]
        if changes.spend_alert_recipients is not None
        else current.spend_alert_recipients
    )
    await repository.save_pilot_config(
        session,
        current.partner,
        cost_per_click_pence=(
            changes.cost_per_click_pence
            if changes.cost_per_click_pence is not None
            else current.cost_per_click_pence
        ),
        spend_alert_thresholds_pence=thresholds,
        spend_alert_recipients=recipients,
        last_alerted_threshold_pence=0
        if changes.reset_spend_alerts
        else current.last_alerted_threshold_pence,
    )
    return await read_config(session, partner=current.partner)


async def check_spend_alerts(session: AsyncSession, *, now: datetime) -> list[str]:
    """Email each pilot partner's recipients once its estimated spend crosses a threshold.

    Judged on the whole pilot so far rather than on whatever range a screen
    last asked for, which is where b2c ran it: there, the same spend alerted or
    not depending on the dates someone had picked. Returns the partners alerted.
    The email is queued in this transaction together with the new
    `last_alerted_threshold_pence`, so a threshold is never both skipped and
    unsent.
    """
    alerted: list[str] = []
    today = now.astimezone(UTC).date()
    for partner in sorted(domain.PILOT_PARTNERS):
        first_landed = await repository.first_arrival_at(session, partner)
        if first_landed is None:
            continue  # nobody has clicked, so nothing has been spent
        config = await read_config(session, partner=partner)
        spend = await _spend(
            session,
            partner,
            first_landed.astimezone(UTC).date(),
            today,
            cost_per_click_pence=config.cost_per_click_pence,
        )
        threshold = domain.threshold_to_alert(
            thresholds_pence=config.spend_alert_thresholds_pence,
            spend_pence=spend.estimated_spend_pence,
            last_alerted_pence=config.last_alerted_threshold_pence,
        )
        if threshold is None:
            continue
        recipients = config.spend_alert_recipients or [get_settings().support_email]
        for recipient in recipients:
            await notifications.enqueue_email(
                session,
                recipient=recipient,
                subject=(
                    f"{partner.upper()} pilot spend alert — estimated "
                    f"{domain.format_gbp(spend.estimated_spend_pence)} "
                    f"({spend.from_date.isoformat()} to {spend.to_date.isoformat()})"
                ),
                template_key=SPEND_ALERT_TEMPLATE,
                payload={
                    "partner": partner.upper(),
                    "from_date": spend.from_date.isoformat(),
                    "to_date": spend.to_date.isoformat(),
                    "estimated_spend": domain.format_gbp(spend.estimated_spend_pence),
                    "threshold": domain.format_gbp(threshold),
                    "estimated_clicks": str(spend.estimated_click_count),
                    "cost_per_click": domain.format_gbp(spend.cost_per_click_pence),
                    "gross_revenue": domain.format_gbp(spend.gross_revenue_pence),
                    "net_margin": domain.format_gbp(spend.net_margin_pence),
                    "disclaimer": spend.billing_disclaimer,
                },
                # The day is in the key: a retried run is deduplicated, but a threshold that
                # alerts again after the thresholds were reset is not swallowed forever.
                idempotency_key=f"partner_spend_alert:{partner}:{threshold}:{today.isoformat()}:{recipient}",
            )
        await repository.save_pilot_config(
            session,
            partner,
            cost_per_click_pence=config.cost_per_click_pence,
            spend_alert_thresholds_pence=config.spend_alert_thresholds_pence,
            spend_alert_recipients=config.spend_alert_recipients,
            last_alerted_threshold_pence=threshold,
        )
        log.info("partner spend alert queued", partner=partner, threshold_pence=threshold)
        alerted.append(partner)
    return alerted


async def _spend(
    session: AsyncSession, partner: str, from_date: date, to_date: date, *, cost_per_click_pence: int
) -> PartnerSpendRead:
    """The spend estimate for one partner and range, at the given rate."""
    window_start, window_end = domain.ledger_bounds(from_date, to_date)
    arrivals = await repository.count_arrivals_between(
        session, partner, landed_from=window_start, landed_before=window_end
    )
    acquired = await repository.acquired_user_ids_between(
        session, partner, acquired_from=window_start, acquired_before=window_end
    )
    revenue = await billing.revenue_for_users(
        session, acquired, paid_from=window_start, paid_before=window_end
    )
    estimate = domain.estimate_spend(
        arrivals=arrivals,
        acquisitions=len(acquired),
        gross_revenue_pence=revenue,
        cost_per_click_pence=cost_per_click_pence,
    )
    return PartnerSpendRead(
        partner=partner,
        from_date=from_date,
        to_date=to_date,
        estimated_click_count=estimate.estimated_click_count,
        cost_per_click_pence=estimate.cost_per_click_pence,
        estimated_spend_pence=estimate.estimated_spend_pence,
        gross_revenue_pence=estimate.gross_revenue_pence,
        net_margin_pence=estimate.net_margin_pence,
        cost_per_acquisition_pence=estimate.cost_per_acquisition_pence,
        acquired_user_count=len(acquired),
    )


def require_partner(partner: str) -> str:
    """The partner key, lower-cased, or `unknown_partner` if it is not in the pilot."""
    partner_key = (partner or "").strip().lower()
    if partner_key not in domain.PILOT_PARTNERS:
        raise errors.UnknownPartnerError()
    return partner_key


def require_bucket(bucket: str) -> str:
    """The bucket name, or `InvalidInput` if it names none of day/week/month."""
    try:
        return domain.validate_bucket(bucket)
    except domain.InvalidBucket as error:
        raise errors.InvalidBucketError(str(error)) from error


def require_range(from_date: date, to_date: date) -> None:
    """Refuse a range that ends before it begins."""
    try:
        domain.ensure_date_range(from_date, to_date)
    except domain.InvalidDateRange as error:
        raise errors.InvalidDateRangeError() from error
