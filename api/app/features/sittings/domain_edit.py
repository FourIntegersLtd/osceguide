"""What may still be changed about a sitting, and when it stops being changeable.

`mode`, `programme_id` and `sitting_type` freeze once any circuit has started,
because they decide what a mark means. The name and the date stay editable for
the life of the record.
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
    which a paused or finished circuit would slip through. Once a circuit has
    opened its room and put a candidate in front of a patient, the examination
    is fixed.
    """

    begun: bool


class SittingLocked(Exception):
    """An assessment-bearing field was asked to change after the sitting had begun."""


class TraineeAlreadyOnCircuit(Exception):
    """Somebody was about to be added to a circuit they are already rostered on."""


class StationNotOnCircuit(Exception):
    """A station was named that this circuit does not run."""


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

    A sitting's mode is what its circuits are composed *from*, and editing a
    sitting re-composes nothing. Flipping the mode over existing circuits would
    leave a sitting labelled `exam` holding three candidates at one station,
    and every route that reads the sitting's mode would then be wrong.
    """
    if circuit_count:
        raise InvalidCircuit(
            "The mode composes a sitting's circuits, so it is chosen before they exist. "
            "Rebuild each circuit, or schedule another sitting."
        )


def ensure_not_already_rostered(existing: Iterable[object], adding: Iterable[object]) -> None:
    """Nobody is put on a circuit twice.

    Checked here rather than left to the database's unique constraint, which
    would otherwise surface as a 500 instead of a clear refusal.
    """
    already = {str(item) for item in existing}
    clash = sorted({str(item) for item in adding} & already)
    if clash:
        raise TraineeAlreadyOnCircuit("Already on this circuit: " + ", ".join(clash) + ".")


def ensure_appended_pairing(trainee_count: int, station_count: int) -> None:
    """Either no station is named and everyone takes the one being run, or one
    is named per arrival — the positional pairing `CreateCircuit` already uses.

    The middle case is the dangerous one: a short list, read as "repeat the last
    station", quietly sends three latecomers to the same room when the circuit
    has three stations and they were meant to spread across them.
    """
    if station_count and station_count != trainee_count:
        raise InvalidCircuit(
            f"Appending {trainee_count} trainees needs {trainee_count} stations, not {station_count}."
        )


def ensure_stations_are_on_circuit(planned: Iterable[object], circuit_stations: Iterable[object]) -> None:
    """A late arrival is placed at a station this circuit already runs.

    Naming a station nobody on this circuit is sitting changes what the
    circuit *is*, which is a structural edit, refused for its own reasons.

    Raises `StationNotOnCircuit` rather than `InvalidCircuit`: the client
    shows this one on the station picker rather than resending the whole form.
    """
    known = {str(item) for item in circuit_stations}
    unknown = sorted({str(item) for item in planned} - known)
    if unknown:
        raise StationNotOnCircuit("Not a station on this circuit: " + ", ".join(unknown) + ".")
