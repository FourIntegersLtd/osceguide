"""Who an organisation teaches, and who is on a circuit.

Group membership is a real table, not a string match against a `cohort` label:
label matching lets a rename silently empty a group, two groups collide on the
same label, and a trainee sit in only one group. A label match survives only as
a one-time importer that writes real membership rows.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


class TraineeRevoked(Exception):
    pass


@dataclass(frozen=True)
class TraineeState:
    access_revoked: bool


@dataclass(frozen=True)
class GroupRef:
    group_id: str
    members: Sequence[str]


@dataclass(frozen=True)
class RosterWarning:
    code: str
    group_id: str


def normalize_email(raw: str) -> str:
    return raw.strip().lower()


def normalize_label(raw: str) -> str:
    """Collapse whitespace and case, as b2b's match does."""
    return " ".join(raw.split()).lower()


def ensure_rosterable(trainee: TraineeState) -> None:
    if trainee.access_revoked:
        raise TraineeRevoked("That trainee's access has been revoked; restore it before rostering them.")


def resolve_roster(
    *, explicit: Sequence[str], groups: Sequence[GroupRef]
) -> tuple[list[str], list[RosterWarning]]:
    """Everyone on a circuit: named trainees first, then group members.

    Order matters because a training circuit pairs trainee *i* with station *i*,
    so the resolved order decides who starts where. An empty group is reported
    rather than passed over — a supervisor who links a group and silently gets
    nobody discovers it when the examination starts.
    """
    resolved: list[str] = []
    seen: set[str] = set()
    for trainee_id in explicit:
        if trainee_id and trainee_id not in seen:
            seen.add(trainee_id)
            resolved.append(trainee_id)

    warnings: list[RosterWarning] = []
    for group in groups:
        if not group.members:
            warnings.append(RosterWarning(code="empty_group", group_id=group.group_id))
            continue
        for trainee_id in group.members:
            if trainee_id and trainee_id not in seen:
                seen.add(trainee_id)
                resolved.append(trainee_id)
    return resolved, warnings
