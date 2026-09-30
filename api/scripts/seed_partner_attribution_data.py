"""The BMJ demo dataset: a deterministic mix of visitors, signups and payments
for the partner attribution dashboard, with no database connection of its own.

Ported verbatim from b2c's `scripts/partner_attribution_seed_data.py`
`_visitor_specs()` — same visit counts, same campaign and exam cycling, same
plan mix and renewal pattern — so a demo walkthrough of the platform
dashboard shows the same shape of pilot the retiring one did. Only the output
shape changed: b2c wrote Firestore documents; this writes plain dataclasses
that `scripts/seed_partner_attribution.py` turns into Postgres rows directly,
since there is no document store here to mirror.

Every date here is computed backwards from a `reference` day (today, unless a
test pins it), so the funnel always reads as "the last six months" however
long ago this file was last touched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Literal

# The three exams BMJ's pilot covers. Fixed, like the legacy script's own
# `EXAMS` tuple — a fourth pilot exam would need its own plan prices below,
# not just a longer tuple.
PilotExam = Literal["sca", "plab", "ortho"]
PlanLength = Literal["one_month", "three_month", "six_month"]

EXAMS: tuple[PilotExam, ...] = ("sca", "plab", "ortho")
CAMPAIGNS: tuple[str, ...] = ("on-exam-pilot", "spring-push", "newsletter", "webinar")
FIRST_NAMES: tuple[str, ...] = (
    "Amira",
    "James",
    "Priya",
    "Omar",
    "Elena",
    "Kwame",
    "Sofia",
    "Chen",
    "Noah",
    "Fatima",
)

# How long each plan length lasts, in days — used only to compute a synthetic
# `plan_ends_at`, since nothing here grants a live entitlement.
PLAN_DURATION_DAYS: dict[PlanLength, int] = {
    "one_month": 30,
    "three_month": 90,
    "six_month": 180,
}

# Pence, by (exam, plan length). Ported verbatim from the legacy
# `PLAN_PRICES_PENCE`; a discounted payment is 90% of this.
PLAN_PRICES_PENCE: dict[tuple[PilotExam, PlanLength], int] = {
    ("sca", "one_month"): 2499,
    ("sca", "three_month"): 6499,
    ("sca", "six_month"): 9499,
    ("plab", "one_month"): 2299,
    ("plab", "three_month"): 5999,
    ("plab", "six_month"): 8799,
    ("ortho", "one_month"): 2699,
    ("ortho", "three_month"): 6999,
    ("ortho", "six_month"): 9999,
}

# Every seeded row's visitor key, email and payment reference is built from
# this prefix, so `--clean` can find and remove exactly what this script
# wrote (and nothing a real visitor or a different seed run created) without
# a tag column anywhere.
SEED_KEY_PREFIX = "seed_dashboard"
SEED_PARTNER = "bmj"
SEED_REPORTER_EMAIL = "reporter@bmj.com"


@dataclass(frozen=True)
class VisitorSpec:
    """One synthetic visitor: how many times they clicked, whether they
    signed up, and what (if anything) they went on to pay.

    Field-for-field the legacy `VisitorSpec` dataclass — only the docstring
    and the type names changed.
    """

    suffix: str
    exam: PilotExam
    campaign: str
    visit_days_ago: int
    visits: int
    signup: bool
    plan: PlanLength | None = None
    discounted: bool = False
    renew_plan: PlanLength | None = None
    renew_days_ago: int | None = None


def _visitor_specs(today: date) -> list[VisitorSpec]:
    """A deterministic mix that fills the default calendar-month view and the
    1 / 3 / 6 month presets: all three plan lengths, four campaigns, three
    exams. Ported verbatim from the legacy function of the same name —
    the loop bodies, offsets and day maths are unchanged, since the whole
    point is to keep reproducing the same funnel shape.
    """
    days_into_month = (today - today.replace(day=1)).days
    specs: list[VisitorSpec] = []
    index = 0

    def add(
        *,
        visit_days_ago: int,
        visits: int,
        signup: bool,
        plan: PlanLength | None = None,
        discounted: bool = False,
        renew_plan: PlanLength | None = None,
        renew_days_ago: int | None = None,
    ) -> None:
        """Append one more visitor, cycling deterministically through the
        three exams and four campaigns as `index` advances."""
        nonlocal index
        index += 1
        offset = index - 1
        specs.append(
            VisitorSpec(
                suffix=f"{index:02d}",
                exam=EXAMS[offset % len(EXAMS)],
                campaign=CAMPAIGNS[offset % len(CAMPAIGNS)],
                visit_days_ago=visit_days_ago,
                visits=visits,
                signup=signup,
                plan=plan,
                discounted=discounted,
                renew_plan=renew_plan,
                renew_days_ago=renew_days_ago,
            )
        )

    current_month_plans: tuple[PlanLength, ...] = (
        "one_month",
        "three_month",
        "six_month",
        "one_month",
        "three_month",
        "six_month",
        "one_month",
        "three_month",
        "six_month",
        "one_month",
        "three_month",
        "six_month",
    )
    month_span = days_into_month + 1
    for i, plan in enumerate(current_month_plans):
        add(
            visit_days_ago=i % month_span,
            visits=1 + (i % 3),
            signup=True,
            plan=plan,
            discounted=i % 5 == 0,
        )
    for i in range(5):
        add(visit_days_ago=i % month_span, visits=1, signup=True)
    for i in range(8):
        add(visit_days_ago=i % month_span, visits=1 + (i % 2), signup=False)

    last_month_plans: tuple[PlanLength, ...] = (
        "one_month",
        "three_month",
        "six_month",
        "one_month",
        "three_month",
        "six_month",
        "three_month",
        "one_month",
        "six_month",
    )
    for i, plan in enumerate(last_month_plans):
        add(
            visit_days_ago=month_span + 1 + (i * 2),
            visits=1 + (i % 2),
            signup=True,
            plan=plan,
            discounted=i % 3 == 0,
        )
    for i in range(4):
        add(visit_days_ago=month_span + 2 + (i * 3), visits=1, signup=True)
    for i in range(8):
        add(visit_days_ago=month_span + (i * 2), visits=1 + (i % 2), signup=False)

    quarter_plans: tuple[PlanLength, ...] = (
        "six_month",
        "three_month",
        "one_month",
        "six_month",
        "three_month",
        "one_month",
        "six_month",
        "three_month",
        "one_month",
    )
    for i, plan in enumerate(quarter_plans):
        add(
            visit_days_ago=35 + (i * 5),
            visits=1 + (i % 2),
            signup=True,
            plan=plan,
            discounted=i % 4 == 0,
            renew_plan="one_month" if i % 3 == 0 else "three_month" if i % 3 == 1 else None,
            renew_days_ago=(i % month_span) if i % 3 != 2 else None,
        )
    for i in range(4):
        add(visit_days_ago=40 + (i * 8), visits=1, signup=True)
    for i in range(8):
        add(visit_days_ago=38 + (i * 6), visits=1 + (i % 2), signup=False)

    half_year_plans: tuple[PlanLength, ...] = (
        "six_month",
        "three_month",
        "one_month",
        "six_month",
        "three_month",
        "one_month",
    )
    for i, plan in enumerate(half_year_plans):
        add(
            visit_days_ago=95 + (i * 10),
            visits=1,
            signup=True,
            plan=plan,
            discounted=i % 2 == 0,
            renew_plan="six_month" if i < 2 else None,
            renew_days_ago=(2 + i) % month_span if i < 2 else None,
        )
    for i in range(3):
        add(visit_days_ago=100 + (i * 12), visits=1, signup=True)
    for i in range(8):
        add(visit_days_ago=98 + (i * 7), visits=1, signup=False)

    return specs


def _clamp_day(day: date, today: date) -> date:
    """Never schedule anything in the future — a `renew_days_ago` of zero can
    otherwise land tomorrow depending on the month's length."""
    return day if day <= today else today


def _at(day: date, hour: int) -> datetime:
    """A day at a fixed UTC hour, so two rows on the same day still order
    the way the legacy fixture intended (a visit, then a signup, then a
    payment, each a little later in the day)."""
    return datetime(day.year, day.month, day.day, hour, 0, 0, tzinfo=UTC)


def _plan_amount_pence(exam: PilotExam, plan: PlanLength, *, discounted: bool) -> int:
    """This plan's price, 10% off if the visitor's payment was discounted."""
    amount = PLAN_PRICES_PENCE[(exam, plan)]
    return int(amount * 0.9) if discounted else amount


@dataclass(frozen=True)
class PaymentSeed:
    """One settled payment: enough to insert a `billing.Payment` row and
    have it show up correctly in the revenue and breakdown reports."""

    plan_code: str
    exam_code: PilotExam
    plan_length: PlanLength
    amount_pence: int
    paid_at: datetime
    plan_ends_at: datetime
    stripe_payment_intent_id: str
    checkout_session_id: str
    receipt_id: str


@dataclass(frozen=True)
class SignupSeed:
    """One visitor who created an account, with the payments (first purchase
    and, sometimes, a renewal) that account went on to make."""

    email: str
    name: str
    exam_code: PilotExam
    acquired_at: datetime
    payments: tuple[PaymentSeed, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class VisitorSeed:
    """Everything one synthetic visitor did: their clicks, and — if they
    converted — the account and payments that followed."""

    suffix: str
    exam_code: PilotExam
    campaign: str
    visitor_key: str
    ref_id: str
    landing_path: str
    arrival_times: tuple[datetime, ...]
    signup: SignupSeed | None


def build_visitors(reference: date | None = None) -> list[VisitorSeed]:
    """The full demo dataset for one run, anchored to `reference` (today UTC
    by default).

    Funnel shape (same as the legacy fixture, approximately):
    - 100+ link visits over roughly six months
    - 40+ signups linked to those visits
    - 30+ paying users, all three plan lengths, across all three exams.
    """
    today = reference or datetime.now(UTC).date()
    visitors: list[VisitorSeed] = []

    for spec in _visitor_specs(today):
        visitor_key = f"vk_{SEED_KEY_PREFIX}_{spec.suffix}"
        ref_id = f"{SEED_PARTNER}-{spec.exam}"
        landing_path = (
            f"/exams/{spec.exam}?utm_source={SEED_PARTNER}&utm_medium=referral&utm_campaign={spec.campaign}"
        )
        first_visit_day = today - timedelta(days=spec.visit_days_ago)
        arrival_times = tuple(
            _at(_clamp_day(first_visit_day + timedelta(days=visit_number - 1), today), hour=8 + visit_number)
            for visit_number in range(1, spec.visits + 1)
        )

        signup: SignupSeed | None = None
        if spec.signup:
            signup_day = _clamp_day(first_visit_day + timedelta(days=1), today)
            first_name = FIRST_NAMES[int(spec.suffix) % len(FIRST_NAMES)]
            payments: list[PaymentSeed] = []
            if spec.plan is not None:
                payment_day = _clamp_day(signup_day + timedelta(days=1), today)
                payments.append(
                    PaymentSeed(
                        plan_code=f"{spec.exam}_{spec.plan}",
                        exam_code=spec.exam,
                        plan_length=spec.plan,
                        amount_pence=_plan_amount_pence(spec.exam, spec.plan, discounted=spec.discounted),
                        paid_at=_at(payment_day, hour=16),
                        plan_ends_at=_at(
                            payment_day + timedelta(days=PLAN_DURATION_DAYS[spec.plan]), hour=16
                        ),
                        stripe_payment_intent_id=f"pi_{SEED_KEY_PREFIX}_{spec.suffix}",
                        checkout_session_id=f"cs_{SEED_KEY_PREFIX}_{spec.suffix}",
                        receipt_id=f"rcpt_{SEED_KEY_PREFIX}_{spec.suffix}",
                    )
                )
                if spec.renew_plan is not None and spec.renew_days_ago is not None:
                    renew_day = today - timedelta(days=spec.renew_days_ago)
                    if renew_day > payment_day:
                        payments.append(
                            PaymentSeed(
                                plan_code=f"{spec.exam}_{spec.renew_plan}",
                                exam_code=spec.exam,
                                plan_length=spec.renew_plan,
                                amount_pence=_plan_amount_pence(spec.exam, spec.renew_plan, discounted=False),
                                paid_at=_at(renew_day, hour=17),
                                plan_ends_at=_at(
                                    renew_day + timedelta(days=PLAN_DURATION_DAYS[spec.renew_plan]),
                                    hour=17,
                                ),
                                stripe_payment_intent_id=f"pi_{SEED_KEY_PREFIX}_{spec.suffix}_renewal",
                                checkout_session_id=f"cs_{SEED_KEY_PREFIX}_{spec.suffix}_renewal",
                                receipt_id=f"rcpt_{SEED_KEY_PREFIX}_{spec.suffix}_renewal",
                            )
                        )
            signup = SignupSeed(
                email=f"{SEED_KEY_PREFIX}_u_{spec.suffix}@seed.osceguide.test",
                name=f"{first_name} User {spec.suffix}",
                exam_code=spec.exam,
                acquired_at=_at(signup_day, hour=14),
                payments=tuple(payments),
            )

        visitors.append(
            VisitorSeed(
                suffix=spec.suffix,
                exam_code=spec.exam,
                campaign=spec.campaign,
                visitor_key=visitor_key,
                ref_id=ref_id,
                landing_path=landing_path,
                arrival_times=arrival_times,
                signup=signup,
            )
        )

    return visitors


def seed_summary(visitors: list[VisitorSeed]) -> str:
    """One line describing what a run wrote — arrivals, signups, payments and
    total revenue — for the seed script to print after every run."""
    arrival_count = sum(len(visitor.arrival_times) for visitor in visitors)
    signups = [visitor.signup for visitor in visitors if visitor.signup is not None]
    payments = [payment for signup in signups for payment in signup.payments]
    plan_lengths = sorted({payment.plan_length for payment in payments})
    revenue_pence = sum(payment.amount_pence for payment in payments)
    return (
        f"visitors={len(visitors)}, "
        f"arrivals={arrival_count}, "
        f"signups={len(signups)}, "
        f"payments={len(payments)}, "
        f"plan_lengths={','.join(plan_lengths)}, "
        f"revenue_pence={revenue_pence}"
    )
