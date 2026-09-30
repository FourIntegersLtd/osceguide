"""The arithmetic behind a partner pilot's reconciliation and spend alerts (G-1).

Oracles: b2c `reconciliation_service._compute_delta`, `partner_spend_service`
and `partner_spend_alert_service`, and the Mixpanel response shape its client read.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.features.growth import domain
from app.features.growth.mixpanel import mixpanel_where, sum_event_counts


def test_the_delta_is_ledger_minus_mixpanel_as_a_share_of_the_ledger() -> None:
    assert domain.reconcile(ledger_count=200, analytics_count=190) == domain.Reconciliation(
        delta=10, delta_percent=5.0
    )
    assert domain.reconcile(ledger_count=3, analytics_count=4) == domain.Reconciliation(
        delta=-1, delta_percent=-33.33
    )
    assert domain.reconcile(ledger_count=0, analytics_count=5) == domain.Reconciliation(
        delta=-5, delta_percent=None
    )


def test_spend_is_clicks_times_the_rate() -> None:
    estimate = domain.estimate_spend(
        arrivals=10, acquisitions=3, gross_revenue_pence=5_000, cost_per_click_pence=40
    )
    assert estimate.estimated_spend_pence == 400
    assert estimate.net_margin_pence == 4_600
    assert estimate.cost_per_acquisition_pence == 133
    assert (
        domain.estimate_spend(
            arrivals=10, acquisitions=0, gross_revenue_pence=0, cost_per_click_pence=40
        ).cost_per_acquisition_pence
        is None
    )


def test_the_highest_new_threshold_crossed_is_the_one_alerted() -> None:
    thresholds = [5_000, 10_000, 25_000]
    assert (
        domain.threshold_to_alert(thresholds_pence=thresholds, spend_pence=6_000, last_alerted_pence=0)
        == 5_000
    )
    assert (
        domain.threshold_to_alert(thresholds_pence=thresholds, spend_pence=30_000, last_alerted_pence=0)
        == 25_000
    )
    assert (
        domain.threshold_to_alert(thresholds_pence=thresholds, spend_pence=6_000, last_alerted_pence=5_000)
        is None
    )
    assert (
        domain.threshold_to_alert(thresholds_pence=[0, -1], spend_pence=6_000, last_alerted_pence=0) is None
    )


def test_a_date_range_covers_whole_utc_days() -> None:
    start, end = domain.ledger_bounds(date(2026, 9, 1), date(2026, 9, 5))
    assert (start, end) == (datetime(2026, 9, 1, tzinfo=UTC), datetime(2026, 9, 6, tzinfo=UTC))


def test_money_is_written_as_b2c_wrote_it() -> None:
    assert domain.format_gbp(123_450) == "£1,234.50"


def test_mixpanels_daily_counts_are_summed_for_the_event_asked_about() -> None:
    payload = {
        "data": {"values": {"partner_referral_landing": {"2026-09-01": 3, "2026-09-02": 4.0, "x": "?"}}}
    }
    assert sum_event_counts(payload, "partner_referral_landing") == 7
    assert sum_event_counts({"data": {"values": {}}}, "partner_referral_landing") == 0
    assert sum_event_counts("not json", "partner_referral_landing") == 0


def test_the_mixpanel_filter_matches_every_property() -> None:
    assert mixpanel_where({"partner": "bmj", "exam": "sca"}) == (
        'properties["partner"] == "bmj" and properties["exam"] == "sca"'
    )
