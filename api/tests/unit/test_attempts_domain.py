"""The attempt lifecycle and the rules the worker contract depends on.

Invariants A1-A8 from the architecture proposal. The freezing rules are the
important ones: both legacy backends freeze a rendered definition on first
bootstrap, and both freeze it even when the render was degraded.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.features.attempts import domain
from app.features.attempts.domain import Status

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


# --------------------------------------------------------------------------
# A3: the status machine
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (Status.CREATED, Status.RUNNING),
        (Status.RUNNING, Status.INTERACTION_COMPLETE),
        (Status.INTERACTION_COMPLETE, Status.EVALUATED),
        (Status.CREATED, Status.FAILED),
        (Status.RUNNING, Status.FAILED),
        (Status.INTERACTION_COMPLETE, Status.FAILED),
    ],
)
def test_allowed_transitions(start: Status, end: Status) -> None:
    assert domain.transition(start, end) is end


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (Status.EVALUATED, Status.RUNNING),
        (Status.EVALUATED, Status.INTERACTION_COMPLETE),
        (Status.FAILED, Status.RUNNING),
        (Status.CREATED, Status.EVALUATED),
        (Status.RUNNING, Status.EVALUATED),
    ],
)
def test_refused_transitions(start: Status, end: Status) -> None:
    with pytest.raises(domain.InvalidTransition):
        domain.transition(start, end)


def test_an_attempt_cannot_be_completed_twice() -> None:
    """A8. The worker retries delivery, so this is reached in normal operation."""
    with pytest.raises(domain.InvalidTransition):
        domain.transition(Status.INTERACTION_COMPLETE, Status.INTERACTION_COMPLETE)


@pytest.mark.parametrize("status", [Status.EVALUATED, Status.FAILED])
def test_terminal_states_are_terminal(status: Status) -> None:
    assert domain.is_terminal(status)


# --------------------------------------------------------------------------
# A1/A2: freezing the definition
# --------------------------------------------------------------------------


def test_a_definition_freezes_on_a_successful_render() -> None:
    assert domain.should_freeze(render_degraded=False, already_frozen=False)


def test_a_degraded_render_is_never_frozen() -> None:
    """A2, the fix.

    Both backends freeze unconditionally today, so a station that failed to
    resolve pins a generic patient prompt — or a debrief prompt carrying no
    transcript ids, leaving the insights panel empty — to that attempt forever.
    Serve the fallback so the session can run; do not record it.
    """
    assert not domain.should_freeze(render_degraded=True, already_frozen=False)


def test_a_frozen_definition_is_never_replaced() -> None:
    """A1. Re-dispatch replays what was frozen rather than re-rendering against
    today's documents."""
    assert not domain.should_freeze(render_degraded=False, already_frozen=True)


# --------------------------------------------------------------------------
# A7: what the worker may never see
# --------------------------------------------------------------------------


def test_the_bootstrap_payload_never_carries_the_evaluation_policy() -> None:
    definition = {
        "id": "d1",
        "version": 1,
        "framework_id": "sca-rcgp-v1",
        "interaction_profile": {"instructions": "You are the patient."},
        "evaluation_policy": {"primary_model": "gpt-5-mini"},
    }
    payload = domain.bootstrap_definition(definition)
    assert "evaluation_policy" not in payload
    assert payload["interaction_profile"]["instructions"]


def test_a_definition_without_instructions_is_not_servable() -> None:
    """The worker refuses an empty instruction set, so catching it here turns a
    failed job into a clear error at creation time."""
    with pytest.raises(domain.UnrenderableDefinition):
        domain.bootstrap_definition({"id": "d1", "interaction_profile": {"instructions": "  "}})


# --------------------------------------------------------------------------
# A4/A5/A6: idempotency
# --------------------------------------------------------------------------


def test_a_repeated_chunk_is_ignored_rather_than_appended() -> None:
    """A4. Chunk posts repeat: the worker retries and does not read the response."""
    seen = {"m1", "m2"}
    assert not domain.should_store_chunk("m1", seen)
    assert domain.should_store_chunk("m3", seen)


def test_the_completed_transcript_is_accepted_once() -> None:
    assert domain.should_accept_transcript(already_complete=False)
    assert not domain.should_accept_transcript(already_complete=True)


def test_scoring_is_idempotent_per_policy_version() -> None:
    """A6. Re-scoring under a new policy is a new result, not a replacement."""
    assert not domain.should_score(
        scored_versions={"platform-default@1"}, policy_version="platform-default@1"
    )
    assert domain.should_score(scored_versions={"platform-default@1"}, policy_version="kings-rubric@3")


# --------------------------------------------------------------------------
# Attempt kinds
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "field"),
    [
        (domain.Kind.EXAM_SLOT, "slot_id"),
        (domain.Kind.SET_STATION, "set_entry_id"),
        (domain.Kind.DEBRIEF, "source_attempt_id"),
        (domain.Kind.PEER, "peer_session_id"),
    ],
)
def test_each_kind_names_the_reference_it_requires(kind: domain.Kind, field: str) -> None:
    assert domain.required_reference(kind) == field


def test_a_free_practice_attempt_references_nothing_else() -> None:
    assert domain.required_reference(domain.Kind.PRACTICE) is None
