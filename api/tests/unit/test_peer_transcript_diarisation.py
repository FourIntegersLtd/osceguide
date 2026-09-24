"""Recovering doctor and patient turns from one mixed recording.

The recovery itself is a model call; what is worth testing without one is what
this slice does with the answer, because every one of these is a way somebody
else's words end up marked as the candidate's.
"""

from __future__ import annotations

import pytest

from app.core.ports import Transcriber, TranscriptionFailed
from app.features.peer_practice import diariser
from tests.support.fakes import FakeTranscriber


def test_the_transcriber_double_conforms_to_the_port() -> None:
    assert isinstance(FakeTranscriber(), Transcriber)


def test_turns_keep_their_order_and_their_speakers() -> None:
    turns = diariser._clean(
        {
            "messages": [
                {"role": "doctor", "message": "What brings you in?"},
                {"role": "patient", "message": "A headache."},
                {"role": "doctor", "message": "How long for?"},
            ]
        }
    )
    assert [turn["role"] for turn in turns] == ["doctor", "patient", "doctor"]
    assert turns[1]["message"] == "A headache."


def test_a_role_that_is_neither_is_dropped_rather_than_guessed() -> None:
    """Attributing a turn to the wrong speaker marks somebody else's words."""
    turns = diariser._clean(
        {
            "messages": [
                {"role": "Doctor", "message": "Hello."},
                {"role": "examiner", "message": "Two minutes remaining."},
                {"role": "patient", "message": "Hello."},
            ]
        }
    )
    assert [turn["role"] for turn in turns] == ["doctor", "patient"]


def test_empty_turns_are_dropped() -> None:
    turns = diariser._clean(
        {"messages": [{"role": "doctor", "message": "  "}, {"role": "patient", "message": "Yes."}]}
    )
    assert turns == [{"role": "patient", "message": "Yes."}]


@pytest.mark.parametrize(
    "parsed", [{"messages": "not a list"}, ["messages"], {"messages": [{"role": "narrator"}]}]
)
def test_a_shape_that_cannot_be_marked_is_refused(parsed: object) -> None:
    """Better no feedback than feedback built from a transcript nobody has."""
    with pytest.raises(TranscriptionFailed):
        diariser._clean(parsed)


async def test_an_empty_recording_never_reaches_the_model() -> None:
    with pytest.raises(TranscriptionFailed):
        await diariser.to_turns("   ")
