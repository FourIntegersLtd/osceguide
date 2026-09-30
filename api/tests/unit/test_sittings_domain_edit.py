"""The freeze on an amended sitting, and the rules an append answers to.

Oracle: `b2b-api/app/features/sessions/service.py::update_session` — which
blocked mode, template and scope the moment a circuit had an active slot or any
feedback, and let the name and the date through — and
`circuit_service.append_trainees_to_circuit`, whose duplicate refusal was a 409
and whose station pairing was refused before anything was written.
"""

from __future__ import annotations

import pytest

from app.features.sittings import domain, domain_edit
from app.features.sittings.domain import Mode
from app.features.sittings.domain_edit import (
    ASSESSMENT_BEARING,
    SittingEditState,
    StationNotOnCircuit,
    TraineeAlreadyOnCircuit,
    ensure_appended_pairing,
    ensure_mode_changeable,
    ensure_not_already_rostered,
    ensure_sitting_editable,
    ensure_stations_are_on_circuit,
)

FROZEN = SittingEditState(begun=True)
OPEN = SittingEditState(begun=False)


def test_the_assessment_bearing_fields_are_the_named_three() -> None:
    """What an existing mark rests on. The name and the date are not among them."""
    assert frozenset({"mode", "programme_id", "sitting_type"}) == ASSESSMENT_BEARING


def test_renaming_a_begun_sitting_is_allowed() -> None:
    ensure_sitting_editable(FROZEN, changing={"name", "scheduled_for"})


def test_retyping_a_begun_sitting_is_refused() -> None:
    with pytest.raises(domain_edit.SittingLocked):
        ensure_sitting_editable(FROZEN, changing={"sitting_type"})


def test_reprogramming_a_begun_sitting_is_refused() -> None:
    """The programme is in here because the rubric is resolved from it."""
    with pytest.raises(domain_edit.SittingLocked):
        ensure_sitting_editable(FROZEN, changing={"programme_id"})


def test_the_same_field_moves_while_nothing_has_begun() -> None:
    for field in ASSESSMENT_BEARING:
        ensure_sitting_editable(OPEN, changing={field})


def test_the_mode_freezes_over_any_circuit_beginning_a_sitting() -> None:
    with pytest.raises(domain.InvalidCircuit):
        ensure_mode_changeable(circuit_count=1)


def test_the_mode_is_still_free_to_choose_before_the_first_circuit() -> None:
    ensure_mode_changeable(circuit_count=0)


def test_somebody_already_on_the_circuit_is_refused_before_the_database() -> None:
    """b2b answered 409. Here it used to be a unique-constraint failure, which
    reaches the client as a 500 for the same fact."""
    with pytest.raises(TraineeAlreadyOnCircuit):
        ensure_not_already_rostered(["ada", "grace"], ["grace"])


def test_a_first_arrival_is_not_a_duplicate() -> None:
    ensure_not_already_rostered(["ada"], ["grace"])


def test_one_station_per_arrival_or_none_at_all() -> None:
    """A short list read as "repeat the last" crowds two people into one room."""
    ensure_appended_pairing(2, 0)
    ensure_appended_pairing(2, 2)
    with pytest.raises(domain.InvalidCircuit):
        ensure_appended_pairing(2, 1)


def test_a_station_must_be_one_the_circuit_already_runs() -> None:
    ensure_stations_are_on_circuit(["s1", "s2"], ["s1", "s2", "s3"])
    with pytest.raises(StationNotOnCircuit):
        ensure_stations_are_on_circuit(["s9"], ["s1", "s2"])


def test_appending_to_an_exam_circuit_is_still_refused() -> None:
    """The legacy refusal is the ported behaviour, and the reason is C1: an exam
    circuit is one candidate, so a second is a second candidate in one room."""
    with pytest.raises(domain.NotPermittedInMode):
        domain.ensure_can_append_trainees(Mode.EXAM)
    domain.ensure_can_append_trainees(Mode.TRAINING)
