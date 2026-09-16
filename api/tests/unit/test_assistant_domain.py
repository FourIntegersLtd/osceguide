"""Assistant session rules.

The worker's own vocabulary is four types (`livekit_assistant_worker/modes.py`),
and b2c maps its record type `athena-doctor` onto the neutral
`consulting-doctor` at its own boundary. That translation happens once, here.
"""

from __future__ import annotations

import pytest

from app.features.assistant import domain


@pytest.mark.parametrize("session_type", ["help", "onboarding", "dashboard", "consulting-doctor"])
def test_the_four_worker_types(session_type: str) -> None:
    assert domain.worker_type_for(session_type) == session_type


def test_the_legacy_persona_name_is_translated_once() -> None:
    """b2c's records call this persona `athena-doctor`; the worker's enum does
    not. The mapping belongs at the boundary, not in the worker."""
    assert domain.worker_type_for("athena-doctor") == "consulting-doctor"


def test_an_unknown_type_is_refused() -> None:
    with pytest.raises(domain.UnknownAssistantType):
        domain.worker_type_for("chatbot")


def test_only_help_sessions_keep_a_transcript() -> None:
    """Oracle: `modes.py` — the other three keep nothing, and b2c's backend
    confirms it at the receiving end."""
    assert domain.keeps_transcript("help")
    for other in ("onboarding", "dashboard", "consulting-doctor"):
        assert not domain.keeps_transcript(other)


def test_instructions_must_be_rendered_before_dispatch() -> None:
    """The worker refuses a session with blank instructions, so an empty render
    must not reach it."""
    with pytest.raises(domain.UnrenderableSession):
        domain.ensure_dispatchable(instructions="   ")


def test_rendered_instructions_are_dispatchable() -> None:
    domain.ensure_dispatchable(instructions="You are helping someone use the app.")


def test_a_finished_session_cannot_be_rejoined() -> None:
    assert domain.can_join(status="active")
    assert not domain.can_join(status="completed")
