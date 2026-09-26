"""Attributing a signup to the partner who sent the visitor.

Commercial, so the rules are strict: a reference we do not recognise is
attributed to nobody rather than guessed at, because the alternative is money
owed to the wrong party.
"""

from __future__ import annotations

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
