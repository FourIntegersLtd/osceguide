"""What may still be changed about a sitting, and when it stops being changeable.

Split from `domain.py` along the seam that file already draws: that one decides
how a sitting is *composed*, this one what may be amended once it has been. The
two refuse for the same reason — `ensure_editable` will not rebuild a circuit
once a station means something — but they are asked at different moments, by
different routes, and about different things.

Ported from b2b's `update_session`, which froze `mode`, the feedback template
and the session's scope (`examId`, `cohortId`, `sessionType`) as soon as any
circuit on it had an active slot or any feedback at all, and let the name and
the date through regardless. b2b's `force` override is not ported: it existed
because that backend could rebuild a session's slots out of the JSON it kept,
and here a forced change would move the rubric or the composition under a
recording that was marked against the other one.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.features.sittings.domain import InvalidCircuit

# The fields an existing mark rests on. Change one and what a review or a
# result means changes with it, which is why they freeze at a different moment
# from the name and the date. `programme_id` is here because the rubric a
# sitting is marked against is resolved through its programme.
ASSESSMENT_BEARING = frozenset({"mode", "programme_id", "sitting_type"})


@dataclass(frozen=True)
class SittingEditState:
    """Whether this sitting has begun producing anything.

    `begun` is any circuit having started — not merely having an active slot,
    which is what b2b asked and which a paused or finished circuit slips
    through. A circuit that has started has opened its room and put a candidate
    in front of a patient; after that, the examination is fixed.
    """

    begun: bool


class SittingLocked(Exception):
    pass


class TraineeAlreadyOnCircuit(Exception):
    pass


class StationNotOnCircuit(Exception):
    pass


def ensure_sitting_editable(state: SittingEditState, *, changing: set[str]) -> None:
    """An assessment-bearing change is refused once anybody has been examined.

    Renaming and re-dating stay open for the life of the record: a sitting
    called the wrong thing, or moved a week, misleads nobody about a mark that
    has already been given. Its mode, its type and the programme that supplies
    its rubric are not like that.
    """
    frozen = sorted(changing & ASSESSMENT_BEARING)
    if frozen and state.begun:
        raise SittingLocked(
            f"{' and '.join(frozen)} cannot change once this sitting has begun. "
            "Change the circuits themselves, or schedule another sitting."
        )


def ensure_mode_changeable(*, circuit_count: int) -> None:
    """The mode of a sitting that already has circuits is not this route's to move.

    A sitting's mode is what its circuits are composed *from* — an exam circuit
    is one candidate through every station, a training circuit pairs each person
    with a position — and editing a sitting re-composes nothing. Flipping the
    mode over the top of existing circuits would leave a sitting labelled `exam`
    holding three candidates at one station, and every route that reads the
    sitting's mode would then be wrong about them. b2b allowed it because its
    circuits carried their own mode-independent JSON; these do not.
    """
    if circuit_count:
        raise InvalidCircuit(
            "The mode composes a sitting's circuits, so it is chosen before they exist. "
            "Rebuild each circuit, or schedule another sitting."
        )


def ensure_not_already_rostered(existing: Iterable[object], adding: Iterable[object]) -> None:
    """Nobody is put on a circuit twice.

    b2b refused it with 409, "Trainee X is already on this circuit". Here a
    second attempt reached the database and came back as a unique-constraint
    failure, which is the same refusal spelled as a 500.
    """
    already = {str(item) for item in existing}
    clash = sorted({str(item) for item in adding} & already)
    if clash:
        raise TraineeAlreadyOnCircuit("Already on this circuit: " + ", ".join(clash) + ".")


def ensure_appended_pairing(trainees: int, stations: int) -> None:
    """Either no station is named and everyone takes the one being run, or one
    is named per arrival — the positional pairing `CreateCircuit` already uses.

    The middle case is the dangerous one: a short list, read as "repeat the last
    station", quietly sends three latecomers to the same room when the circuit
    has three stations and they were meant to spread across them.
    """
    if stations and stations != trainees:
        raise InvalidCircuit(f"Appending {trainees} trainees needs {trainees} stations, not {stations}.")


def ensure_stations_are_on_circuit(planned: Iterable[object], circuit_stations: Iterable[object]) -> None:
    """A late arrival is placed at a station this circuit already runs.

    Narrower than b2b, which checked the station against the organisation and so
    let a brand-new one into a live circuit. A station nobody on this circuit is
    sitting is not where a latecomer belongs — naming one changes what the
    circuit *is*, and that is the structural edit, refused for its own reasons.

    Its own code rather than `invalid_circuit`, because the client answers this
    one with a message on the station picker and answers a bad pairing by sending
    the form again with both lists complete.
    """
    known = {str(item) for item in circuit_stations}
    unknown = sorted({str(item) for item in planned} - known)
    if unknown:
        raise StationNotOnCircuit("Not a station on this circuit: " + ", ".join(unknown) + ".")
