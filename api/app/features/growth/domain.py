"""Attributing a signup to the partner who sent the visitor.

Commercial, so the rules are strict: a reference we do not recognise is
attributed to nobody rather than guessed at, because the alternative is money
owed to the wrong party.

Ported from `b2c/shared/constants/partner_attribution_constants.py`.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime, timedelta

PILOT_PARTNERS = frozenset({"bmj"})

# Which exams are in the pilot is not a constant here any more: it is the
# `partner_pilot` flag on each exam row, so adding an exam to the pilot is an
# admin toggling it rather than a code change. Callers pass the set in.

# Oracle: the 90-day acquisition cookie.
ATTRIBUTION_WINDOW = timedelta(days=90)

_LANDING_PREFIX = "/exams/"


class UnknownPartner(ValueError):
    pass


class ExamNotInPilot(ValueError):
    pass


def format_ref_id(partner: str, exam: str, *, pilot_exams: Collection[str]) -> str:
    partner_key = (partner or "").strip().lower()
    exam_key = (exam or "").strip().lower()
    if partner_key not in PILOT_PARTNERS:
        raise UnknownPartner(f"{partner!r} is not a pilot partner.")
    if exam_key not in pilot_exams:
        raise ExamNotInPilot(f"{exam!r} is not in the pilot.")
    return f"{partner_key}-{exam_key}"


def parse_ref_id(ref_id: str, *, pilot_exams: Collection[str]) -> tuple[str, str] | None:
    """The partner and exam a reference names, or nothing.

    Never guessed: an unrecognised reference credits nobody, because crediting
    the wrong partner is worse than crediting none.
    """
    partner, _, exam = (ref_id or "").strip().lower().partition("-")
    if partner in PILOT_PARTNERS and exam in pilot_exams:
        return partner, exam
    return None


def exam_from_landing_path(path: str, *, pilot_exams: Collection[str]) -> str | None:
    cleaned = (path or "").strip().lower()
    if not cleaned.startswith(_LANDING_PREFIX):
        return None
    exam = cleaned[len(_LANDING_PREFIX) :].strip("/")
    return exam if exam in pilot_exams else None


def landing_path_for(exam: str) -> str:
    """Where a partner's link for this exam should point.

    The inverse of `exam_from_landing_path`, so the path a partner is given and
    the path this slice recognises cannot drift apart.
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
    arrivals: int
    signups: int
    purchases: int

    @property
    def signup_rate(self) -> float:
        return self.signups / self.arrivals if self.arrivals else 0.0

    @property
    def purchase_rate(self) -> float:
        """Of those who signed up, not of everyone who arrived.

        A share of the stage before is the only reading that tells you where
        people are being lost.
        """
        return self.purchases / self.signups if self.signups else 0.0


def funnel(*, arrivals: int, signups: int, purchases: int) -> Funnel:
    return Funnel(arrivals=arrivals, signups=signups, purchases=purchases)
