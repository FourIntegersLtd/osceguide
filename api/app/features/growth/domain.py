"""Attributing a signup to the partner who sent the visitor.

Commercial, so the rules are strict: a reference we do not recognise is
attributed to nobody rather than guessed at, because the alternative is money
owed to the wrong party.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

PILOT_PARTNERS = frozenset({"bmj"})

# Which exams are in the pilot is the `partner_pilot` flag on each exam row,
# not a constant here, so adding one is an admin toggling it, not a code
# change. Callers pass the set in.

_LANDING_PREFIX = "/exams/"


class UnknownPartner(ValueError):
    """Raised when a partner code names nobody in `PILOT_PARTNERS`."""

    pass


class ExamNotInPilot(ValueError):
    """Raised when an exam is not one of the exams a partner pilot covers."""

    pass


def format_ref_id(partner: str, exam: str, *, pilot_exams: Collection[str]) -> str:
    """Build the reference a partner should put in its link for one exam.

    The inverse of `parse_ref_id`. Refuses an unknown partner or an exam outside
    the pilot rather than producing a reference nothing can attribute later.
    """
    partner_key = (partner or "").strip().lower()
    exam_key = (exam or "").strip().lower()
    if partner_key not in PILOT_PARTNERS:
        raise UnknownPartner(f"{partner!r} is not a pilot partner.")
    if exam_key not in pilot_exams:
        raise ExamNotInPilot(f"{exam!r} is not in the pilot.")
    return f"{partner_key}-{exam_key}"


def parse_ref_id(ref_id: str, *, pilot_exams: Collection[str]) -> tuple[str, str] | None:
    """The partner and exam a reference names, or nothing.

    Never guessed: an unrecognised reference credits nobody.
    """
    partner, _, exam = (ref_id or "").strip().lower().partition("-")
    if partner in PILOT_PARTNERS and exam in pilot_exams:
        return partner, exam
    return None


def exam_from_landing_path(path: str, *, pilot_exams: Collection[str]) -> str | None:
    """The pilot exam a landing path names, or nothing if it names none.

    The inverse of `landing_path_for`, so the two cannot drift apart.
    """
    cleaned = (path or "").strip().lower()
    if not cleaned.startswith(_LANDING_PREFIX):
        return None
    exam = cleaned[len(_LANDING_PREFIX) :].strip("/")
    return exam if exam in pilot_exams else None


def landing_path_for(exam: str) -> str:
    """Where a partner's link for this exam should point.

    The inverse of `exam_from_landing_path`, so the two cannot drift apart.
    """
    return f"{_LANDING_PREFIX}{exam}"


def attributes(*, arrived_at: datetime, signed_up_at: datetime) -> bool:
    """Whether an arrival can be credited with a signup.

    Any arrival before the signup counts, however long ago: once a partner's
    link is clicked, that partner is credited. Only one after the signup does
    not — somebody who followed a partner link after signing up was not sent by
    that partner.
    """
    return arrived_at <= signed_up_at


@dataclass(frozen=True)
class Funnel:
    """One partner's conversion so far: how many arrived, signed up and paid."""

    arrivals: int
    signups: int
    purchases: int

    @property
    def signup_rate(self) -> float:
        return self.signups / self.arrivals if self.arrivals else 0.0

    @property
    def purchase_rate(self) -> float:
        """Of those who signed up, not of everyone who arrived — the reading
        that shows where people are being lost."""
        return self.purchases / self.signups if self.signups else 0.0


def funnel(*, arrivals: int, signups: int, purchases: int) -> Funnel:
    return Funnel(arrivals=arrivals, signups=signups, purchases=purchases)


# --- referral payouts -------------------------------------------------------

# A referral is `unpaid` until somebody settles it by hand and says so.
# Deliberately no third state — "pending" would describe the queue, not the
# money.
PAYOUT_STATUSES = ("unpaid", "paid")


def normalise_payout_status(payout_status: str) -> str:
    """Lower-cased, validated payout status, or a `ValueError` if it is neither."""
    key = (payout_status or "").strip().lower()
    if key not in PAYOUT_STATUSES:
        raise ValueError(f"A payout is {' or '.join(PAYOUT_STATUSES)}, not {payout_status!r}.")
    return key


# --- referral rewards -------------------------------------------------------

# Oracle: b2c `payment_service._update_user_subscription`. A referrer earns
# £2.50 when their code buys a one-month plan and £5 when it buys anything
# longer. Constants rather than database values: the same for everyone, so a
# change is a deploy, not a data change.
ONE_MONTH_PLAN_DAYS = 30
ONE_MONTH_REFERRAL_REWARD_PENCE = 250
LONGER_PLAN_REFERRAL_REWARD_PENCE = 500


def referral_reward_pence(plan_duration_days: int) -> int:
    """What a referrer earns when their code buys a plan lasting this many days."""
    if plan_duration_days <= ONE_MONTH_PLAN_DAYS:
        return ONE_MONTH_REFERRAL_REWARD_PENCE
    return LONGER_PLAN_REFERRAL_REWARD_PENCE


# --- referral payout bank details --------------------------------------------

# Oracle: the retiring client's `BankDetails.tsx`, which accepted a sort code
# either grouped ("12-34-56") or bare ("123456") — a UK sort code is always
# three pairs of digits identifying a bank branch, never anything longer or
# shorter.
SORT_CODE_PATTERN = re.compile(r"^\d{2}-?\d{2}-?\d{2}$")
SORT_CODE_DIGITS = 6

# The legacy form never enforced a specific length; UK account numbers are
# eight digits in practice, but building societies and some international
# transfers use fewer or a couple more, so this accepts the same 6-10 digit
# range the corrected spec calls for rather than the legacy client's
# unenforced free text.
ACCOUNT_NUMBER_MIN_DIGITS = 6
ACCOUNT_NUMBER_MAX_DIGITS = 10
ACCOUNT_NUMBER_PATTERN = re.compile(rf"^\d{{{ACCOUNT_NUMBER_MIN_DIGITS},{ACCOUNT_NUMBER_MAX_DIGITS}}}$")


class InvalidSortCode(ValueError):
    """A sort code did not match "12-34-56" or "123456"."""


class InvalidAccountNumber(ValueError):
    """An account number was not 6–10 digits."""


def normalise_sort_code(sort_code: str) -> str:
    """A sort code, stripped of its separators down to six digits for storage.

    Accepts either the grouped or bare legacy form; always stores and later
    displays the grouped form, since that is what someone recognises as a sort
    code rather than a phone number.
    """
    candidate = (sort_code or "").strip()
    if not SORT_CODE_PATTERN.match(candidate):
        raise InvalidSortCode(f"{sort_code!r} is not a sort code (expected 12-34-56 or 123456).")
    return candidate.replace("-", "")


def format_sort_code(digits: str) -> str:
    """The six stored digits, grouped for display: "123456" -> "12-34-56"."""
    return f"{digits[0:2]}-{digits[2:4]}-{digits[4:6]}"


def validate_account_number(account_number: str) -> str:
    """An account number, unchanged but checked to be 6-10 digits."""
    candidate = (account_number or "").strip()
    if not ACCOUNT_NUMBER_PATTERN.match(candidate):
        raise InvalidAccountNumber(
            f"An account number is {ACCOUNT_NUMBER_MIN_DIGITS}-{ACCOUNT_NUMBER_MAX_DIGITS} digits."
        )
    return candidate


# --- reconciliation and spend (G-1) -----------------------------------------------

# Oracle: b2c `partner_attribution_constants.PARTNER_REFERRAL_LANDING_EVENT`, the
# event platform-web fires when somebody lands from a partner link.
PARTNER_LANDING_EVENT = "partner_referral_landing"

# Oracle: b2c `PartnerPilotConfigModel`. £0.40 a click, and alerts at £500,
# £1,000 and £2,500 of estimated spend.
DEFAULT_COST_PER_CLICK_PENCE = 40
DEFAULT_SPEND_ALERT_THRESHOLDS_PENCE = (50_000, 100_000, 250_000)

# Oracle: b2c `click_count_source` — the only way clicks are estimated.
CLICK_COUNT_SOURCE = "osce_raw_arrivals_proxy"

# Oracle: b2c `BMJ_SPEND_BILLING_DISCLAIMER`, verbatim. The partner bills on its
# own click records; this figure is ours and says so.
SPEND_BILLING_DISCLAIMER = (
    "This is a rough estimate only. We count link visits on OSCE Guide and multiply "
    "by our agreed rate per visit. BMJ invoices based on their own click records, "
    "so this won't match what they bill you."
)


class InvalidDateRange(ValueError):
    """Raised when a reporting range ends before it starts."""


def ensure_date_range(from_date: date, to_date: date) -> None:
    """Refuse a range that ends before it begins; one day is `from == to`."""
    if from_date > to_date:
        raise InvalidDateRange("from_date must be on or before to_date")


def ledger_bounds(from_date: date, to_date: date) -> tuple[datetime, datetime]:
    """The UTC instants an inclusive date range covers, end exclusive.

    b2c compared against `T23:59:59Z` and so dropped the day's last second;
    the start of the next day is the honest end.
    """
    start = datetime.combine(from_date, time.min, tzinfo=UTC)
    return start, datetime.combine(to_date, time.min, tzinfo=UTC) + timedelta(days=1)


@dataclass(frozen=True)
class Reconciliation:
    """How far the analytics count is from our own ledger."""

    delta: int
    # `delta` as a share of the ledger, or None when the ledger is empty.
    delta_percent: float | None


def reconcile(*, ledger_count: int, analytics_count: int) -> Reconciliation:
    """Oracle: b2c `_compute_delta` — ledger minus analytics, as a percentage of the ledger."""
    delta = ledger_count - analytics_count
    if ledger_count == 0:
        return Reconciliation(delta=delta, delta_percent=None)
    return Reconciliation(delta=delta, delta_percent=round(delta / ledger_count * 100, 2))


@dataclass(frozen=True)
class SpendEstimate:
    """What a partner's clicks are estimated to have cost, and what they brought in."""

    estimated_click_count: int
    cost_per_click_pence: int
    estimated_spend_pence: int
    gross_revenue_pence: int
    net_margin_pence: int
    cost_per_acquisition_pence: int | None


def estimate_spend(
    *, arrivals: int, acquisitions: int, gross_revenue_pence: int, cost_per_click_pence: int
) -> SpendEstimate:
    """Oracle: b2c `build_partner_spend_report`. Every arrival is taken as a paid click."""
    clicks = max(0, arrivals)
    spend = clicks * cost_per_click_pence
    return SpendEstimate(
        estimated_click_count=clicks,
        cost_per_click_pence=cost_per_click_pence,
        estimated_spend_pence=spend,
        gross_revenue_pence=gross_revenue_pence,
        net_margin_pence=gross_revenue_pence - spend,
        cost_per_acquisition_pence=spend // acquisitions if acquisitions > 0 else None,
    )


def threshold_to_alert(
    *, thresholds_pence: Collection[int], spend_pence: int, last_alerted_pence: int
) -> int | None:
    """Oracle: b2c `maybe_send_spend_threshold_alerts`. The highest threshold the
    spend has reached that has not been alerted yet, or None.

    One email for a jump across several thresholds, naming the highest: each
    threshold alerts at most once until the alerts are reset.
    """
    crossed = [
        threshold
        for threshold in {value for value in thresholds_pence if value > 0}
        if spend_pence >= threshold and threshold > last_alerted_pence
    ]
    return max(crossed) if crossed else None


def normalise_thresholds(thresholds_pence: Collection[int]) -> list[int]:
    """Oracle: b2c's config update — distinct, non-negative, ascending."""
    return sorted({int(value) for value in thresholds_pence if value >= 0})


def format_gbp(pence: int) -> str:
    """Oracle: b2c `_format_gbp` — `£1,234.50`."""
    return f"£{pence / 100:,.2f}"


# --- time buckets (BMJ dashboard "over time" charts) -------------------------

# A chart's `bucket` query param: `date_trunc` is asked to do the grouping in
# Postgres, but only for the buckets that have a row in them, so every "over
# time" endpoint gap-fills the empty ones with these pure functions before it
# is honest about what an empty week looks like on a chart.
VALID_BUCKETS = frozenset({"day", "week", "month"})


class InvalidBucket(ValueError):
    """Raised when a `bucket` query param names none of `day`, `week`, `month`."""


def validate_bucket(bucket: str) -> str:
    """The bucket name, unchanged, or `InvalidBucket` if it names none of the three."""
    if bucket not in VALID_BUCKETS:
        raise InvalidBucket(f"bucket must be one of {sorted(VALID_BUCKETS)}, not {bucket!r}")
    return bucket


def bucket_start(day: date, bucket: str) -> date:
    """The first day of the bucket this date falls in.

    Matches Postgres' own `date_trunc`: a week starts on Monday (ISO, not the
    US Sunday), a month on its first day, a day is itself.
    """
    if bucket == "day":
        return day
    if bucket == "week":
        return day - timedelta(days=day.weekday())
    if bucket == "month":
        return day.replace(day=1)
    raise InvalidBucket(f"bucket must be one of {sorted(VALID_BUCKETS)}, not {bucket!r}")


def advance_bucket(start: date, bucket: str) -> date:
    """The first day of the bucket after this one."""
    if bucket == "day":
        return start + timedelta(days=1)
    if bucket == "week":
        return start + timedelta(weeks=1)
    if bucket == "month":
        return date(start.year + 1, 1, 1) if start.month == 12 else date(start.year, start.month + 1, 1)
    raise InvalidBucket(f"bucket must be one of {sorted(VALID_BUCKETS)}, not {bucket!r}")


def iter_bucket_starts(from_date: date, to_date: date, bucket: str) -> Iterator[date]:
    """Every bucket start from the one `from_date` falls in to the one `to_date`
    falls in, inclusive — the full x-axis a chart draws, gaps and all.
    """
    current = bucket_start(from_date, bucket)
    last = bucket_start(to_date, bucket)
    while current <= last:
        yield current
        current = advance_bucket(current, bucket)


# --- anomaly detection (BMJ dashboard) ---------------------------------------

# Oracle: b2c `bmj_anomaly_service`. A reconciliation delta below this share of
# the ledger is ordinary noise and is not flagged at all.
MIXPANEL_DRIFT_WARNING_PERCENT = 10.0
MIXPANEL_DRIFT_CRITICAL_PERCENT = 25.0


@dataclass(frozen=True)
class Anomaly:
    """One thing about a partner's numbers worth a human's attention.

    `metric` is a short, already-formatted figure for the card ("18.4%",
    "£120.00"), never a number the frontend has to format itself.
    """

    code: str
    severity: str
    title: str
    detail: str
    metric: str | None


def detect_anomalies(
    *,
    reconciliation_status: str,
    reconciliation_delta_percent: float | None,
    raw_arrival_count: int,
    signup_count: int,
    purchase_count: int,
    acquired_user_count: int,
    net_margin_pence: int,
) -> list[Anomaly]:
    """Every anomaly a partner's summary should flag, in a fixed order so the
    dashboard's list does not reshuffle between two loads of the same range.

    Oracle: b2c `bmj_anomaly_service.detect_anomalies` — same five codes, same
    severities. Each rule stands alone: a range can trigger any subset of them,
    including all five or none.
    """
    anomalies: list[Anomaly] = []

    if reconciliation_status != "ok":
        # Mixpanel could not be asked at all; there is nothing to compare, so
        # this is informational rather than a sign that anything is wrong.
        anomalies.append(
            Anomaly(
                code="mixpanel_unavailable",
                severity="info",
                title="Mixpanel could not be reached",
                detail="The ledger count is shown alone for this range; Mixpanel did not answer.",
                metric=reconciliation_status,
            )
        )
    elif reconciliation_delta_percent is not None:
        magnitude = abs(reconciliation_delta_percent)
        if magnitude >= MIXPANEL_DRIFT_CRITICAL_PERCENT:
            anomalies.append(
                Anomaly(
                    code="mixpanel_drift",
                    severity="critical",
                    title="The ledger and Mixpanel disagree sharply",
                    detail=(
                        "Our arrival ledger and Mixpanel's landing count differ by a wide "
                        "margin for this range."
                    ),
                    metric=f"{magnitude:.1f}%",
                )
            )
        elif magnitude >= MIXPANEL_DRIFT_WARNING_PERCENT:
            anomalies.append(
                Anomaly(
                    code="mixpanel_drift",
                    severity="warning",
                    title="The ledger and Mixpanel disagree",
                    detail="Our arrival ledger and Mixpanel's landing count differ for this range.",
                    metric=f"{magnitude:.1f}%",
                )
            )

    if signup_count > raw_arrival_count or purchase_count > signup_count:
        # A later funnel stage can never outnumber the stage before it; seeing
        # one do so means something upstream is double-counted or mis-joined.
        anomalies.append(
            Anomaly(
                code="funnel_order_violation",
                severity="critical",
                title="The funnel is out of order",
                detail="A later stage of the funnel counts more people than the stage before it.",
                metric=f"arrivals={raw_arrival_count} signups={signup_count} purchases={purchase_count}",
            )
        )

    if acquired_user_count != signup_count:
        # The acquisitions ledger (what a partner is paid on) and the funnel's
        # own signup count are two different reads of "how many signed up";
        # they must always agree, so a gap means one of the paths has a bug.
        anomalies.append(
            Anomaly(
                code="acquired_count_mismatch",
                severity="warning",
                title="Acquired users do not match the funnel's signups",
                detail="The acquisitions ledger and the funnel's own signup count disagree for this range.",
                metric=f"acquired={acquired_user_count} signups={signup_count}",
            )
        )

    if net_margin_pence < 0:
        anomalies.append(
            Anomaly(
                code="negative_net_margin",
                severity="warning",
                title="Estimated spend exceeds revenue",
                detail=(
                    "This partner's estimated click spend is more than the revenue it has "
                    "brought in so far in this range."
                ),
                metric=format_gbp(net_margin_pence),
            )
        )

    return anomalies
