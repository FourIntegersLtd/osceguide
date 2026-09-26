"""Pairing two people who want to practise together.

Somebody plays the doctor and somebody plays the patient. The rules are about
fairness: nobody should take the same part twice running, and the person with
less experience gets the doctor's part, which is the one worth practising.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    DOCTOR = "doctor"
    PATIENT = "patient"


class CannotPair(Exception):
    """Raised when two people in the queue cannot be put together."""


@dataclass(frozen=True)
class Waiting:
    """One person's place in the queue, and what the fairness rules need to know about them."""

    user_id: str
    last_role: Role | None = None
    session_count: int = 0
    # b2c hardcodes three personal email addresses that must never be doctor.
    # It is a property of a person, so it belongs on the person.
    never_doctor: bool = False


@dataclass(frozen=True)
class Pair:
    """Who has been matched, and which part each of them plays."""

    doctor: str
    patient: str


def assign_roles(first: Waiting, second: Waiting) -> Pair:
    """Who plays which part, applying the fairness rules in order."""
    if first.user_id == second.user_id:
        raise CannotPair("Somebody cannot practise with themselves.")

    # Overrides everything else.
    if first.never_doctor and second.never_doctor:
        raise CannotPair("Neither of these two can take the doctor's part.")
    if first.never_doctor:
        return Pair(doctor=second.user_id, patient=first.user_id)
    if second.never_doctor:
        return Pair(doctor=first.user_id, patient=second.user_id)

    # Each takes the opposite of last time, so nobody repeats a part.
    if first.last_role and second.last_role and first.last_role != second.last_role:
        if first.last_role is Role.DOCTOR:
            return Pair(doctor=second.user_id, patient=first.user_id)
        return Pair(doctor=first.user_id, patient=second.user_id)

    # A newcomer takes the doctor's part: it is the one worth practising.
    if not first.last_role and second.last_role:
        return Pair(doctor=first.user_id, patient=second.user_id)
    if not second.last_role and first.last_role:
        return Pair(doctor=second.user_id, patient=first.user_id)

    # Otherwise the less experienced person gets it.
    if first.session_count != second.session_count:
        if first.session_count < second.session_count:
            return Pair(doctor=first.user_id, patient=second.user_id)
        return Pair(doctor=second.user_id, patient=first.user_id)

    # Dead level. b2c picks at random; deterministic by id instead, so a
    # failing match can be reproduced. Fairness is already served by the rules
    # above, and a coin toss between two equals adds nothing.
    ordered = sorted([first.user_id, second.user_id])
    return Pair(doctor=ordered[0], patient=ordered[1])


def next_pair(queue: Sequence[Waiting]) -> Pair | None:
    """The next two who can practise together, longest-waiting first.

    A pair that cannot be formed — two people who must both be patient — is
    skipped rather than left blocking everyone behind it.
    """
    for position, first in enumerate(queue):
        for second in queue[position + 1 :]:
            try:
                return assign_roles(first, second)
            except CannotPair:
                continue
    return None
