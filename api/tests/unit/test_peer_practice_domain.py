"""Pairing two strangers and deciding who plays which part.

Ported from `b2c human_practice_service.assign_roles:272-370`. The rules are
about fairness — nobody should play patient twice running, and the less
experienced person gets the harder part — so they are carried over exactly.
"""

from __future__ import annotations

import pytest

from app.features.peer_practice import domain
from app.features.peer_practice.domain import Role


def waiting(
    user_id: str,
    *,
    last_role: Role | None = None,
    sessions: int = 0,
    never_doctor: bool = False,
) -> domain.Waiting:
    return domain.Waiting(
        user_id=user_id, last_role=last_role, session_count=sessions, never_doctor=never_doctor
    )


# --------------------------------------------------------------------------
# Role assignment
# --------------------------------------------------------------------------


def test_someone_who_must_never_be_doctor_is_the_patient() -> None:
    """b2c hardcodes three personal email addresses for this. It is a property
    of a person, so it is a flag rather than a literal in the matcher."""
    pair = domain.assign_roles(waiting("a", never_doctor=True), waiting("b"))
    assert pair.doctor == "b"
    assert pair.patient == "a"


def test_if_both_must_be_patient_they_are_not_matched() -> None:
    """Better unmatched than silently giving someone the part they cannot take."""
    with pytest.raises(domain.CannotPair):
        domain.assign_roles(waiting("a", never_doctor=True), waiting("b", never_doctor=True))


def test_different_last_roles_means_each_swaps() -> None:
    """Oracle: rule 4. Nobody plays the same part twice running."""
    pair = domain.assign_roles(waiting("a", last_role=Role.DOCTOR), waiting("b", last_role=Role.PATIENT))
    assert pair.doctor == "b"
    assert pair.patient == "a"


def test_a_newcomer_takes_the_doctor_part() -> None:
    """Oracle: rule 3. The doctor role is the one worth practising."""
    pair = domain.assign_roles(waiting("new"), waiting("old", last_role=Role.PATIENT, sessions=5))
    assert pair.doctor == "new"


def test_between_two_newcomers_the_less_experienced_is_doctor() -> None:
    """Oracle: rule 2."""
    pair = domain.assign_roles(waiting("quiet", sessions=0), waiting("busy", sessions=4))
    assert pair.doctor == "quiet"


def test_after_the_same_last_role_the_less_experienced_is_doctor() -> None:
    """Oracle: rule 5."""
    pair = domain.assign_roles(
        waiting("quiet", last_role=Role.PATIENT, sessions=1),
        waiting("busy", last_role=Role.PATIENT, sessions=9),
    )
    assert pair.doctor == "quiet"


def test_equal_experience_still_produces_a_pair() -> None:
    """b2c picks at random here. Deterministic by user id instead, so a failing
    match is reproducible — the fairness argument is already satisfied by the
    rules above."""
    pair = domain.assign_roles(waiting("a"), waiting("b"))
    assert {pair.doctor, pair.patient} == {"a", "b"}
    assert domain.assign_roles(waiting("a"), waiting("b")) == pair


def test_nobody_is_matched_with_themselves() -> None:
    with pytest.raises(domain.CannotPair):
        domain.assign_roles(waiting("a"), waiting("a"))


# --------------------------------------------------------------------------
# The queue
# --------------------------------------------------------------------------


def test_the_two_longest_waiting_are_paired() -> None:
    queue = [waiting("first"), waiting("second"), waiting("third")]
    pair = domain.next_pair(queue)
    assert pair is not None
    assert {pair.doctor, pair.patient} == {"first", "second"}


def test_one_person_waiting_is_not_a_pair() -> None:
    assert domain.next_pair([waiting("alone")]) is None


def test_an_unpairable_pair_does_not_block_the_queue() -> None:
    """Two people who must both be patient are skipped over, not left blocking
    everyone behind them."""
    queue = [
        waiting("p1", never_doctor=True),
        waiting("p2", never_doctor=True),
        waiting("d1"),
    ]
    pair = domain.next_pair(queue)
    assert pair is not None
    assert pair.doctor == "d1"
