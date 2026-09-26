"""Attributing a signup to the partner who sent the visitor.

Commercial, so the rules are strict: a reference we do not recognise is
attributed to nobody rather than guessed at, because the alternative is money
owed to the wrong party.
"""

from __future__ import annotations

import re
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime, timedelta

PILOT_PARTNERS = frozenset({"bmj"})

# Which exams are in the pilot is the `partner_pilot` flag on each exam row,
# not a constant here, so adding one is an admin toggling it, not a code
# change. Callers pass the set in.

# Oracle: the 90-day acquisition cookie.
ATTRIBUTION_WINDOW = timedelta(days=90)

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

    Inside the window, and before it — somebody who followed a partner link
    after signing up was not sent by that partner.
    """
    if arrived_at > signed_up_at:
        return False
    return signed_up_at - arrived_at <= ATTRIBUTION_WINDOW


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
