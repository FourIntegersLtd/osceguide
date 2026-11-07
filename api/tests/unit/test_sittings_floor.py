"""Who may speak in a circuit's room: one rule, read by every token and every live change."""

from __future__ import annotations

import uuid

import pytest

from app.features.sittings.floor import OBSERVER_PREFIX, mic_allowed
from app.features.sittings.models import Circuit

CURRENT = uuid.uuid4()
OTHER = uuid.uuid4()
SUPERVISOR = f"{OBSERVER_PREFIX}{uuid.uuid4()}"


def circuit(*, open_floor: bool = False) -> Circuit:
    return Circuit(open_floor=open_floor)


@pytest.mark.parametrize(
    ("identity", "open_floor", "active", "expected"),
    [
        (str(CURRENT), False, CURRENT, True),
        (str(OTHER), False, CURRENT, False),
        (SUPERVISOR, False, CURRENT, True),
        (SUPERVISOR, False, None, True),
        (str(OTHER), True, CURRENT, True),
        (str(OTHER), False, None, False),
    ],
    ids=["current", "other", "supervisor", "supervisor-ended", "open-floor", "nobody-active"],
)
def test_training_mic_rule(identity: str, open_floor: bool, active: uuid.UUID | None, expected: bool) -> None:
    assert mic_allowed(circuit(open_floor=open_floor), active, identity, training=True) is expected


def test_exam_keeps_todays_grants() -> None:
    """An exam candidate always speaks and an examiner never does, whatever the floor says."""
    exam = circuit(open_floor=True)
    assert mic_allowed(exam, CURRENT, str(OTHER), training=False) is True
    assert mic_allowed(exam, CURRENT, SUPERVISOR, training=False) is False
