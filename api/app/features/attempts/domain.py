"""The attempt: one candidate running one scenario, however it was reached.

This is the shared core. A consumer practising alone, a trainee in an exam
slot, a debrief about an earlier attempt and a peer session all produce rows in
one table, because they are the same event with different reasons for being
allowed to happen.

Pure rules; the worker contract and the scoring job both depend on them.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from typing import Any


class Status(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    INTERACTION_COMPLETE = "interaction_complete"
    EVALUATED = "evaluated"
    FAILED = "failed"


class Kind(StrEnum):
    PRACTICE = "practice"
    SET_STATION = "set_station"
    DEBRIEF = "debrief"
    SELF_PRACTICE = "self_practice"
    EXAM_SLOT = "exam_slot"
    PEER = "peer"


class InvalidTransition(Exception):
    pass


class UnrenderableDefinition(Exception):
    """A definition with no instructions. The worker refuses these, so refusing
    them here turns a job that dies on connect into an error at creation."""


TERMINAL = frozenset({Status.EVALUATED, Status.FAILED})

_ALLOWED: Mapping[Status, frozenset[Status]] = {
    Status.CREATED: frozenset({Status.RUNNING, Status.FAILED}),
    Status.RUNNING: frozenset({Status.INTERACTION_COMPLETE, Status.FAILED}),
    Status.INTERACTION_COMPLETE: frozenset({Status.EVALUATED, Status.FAILED}),
    Status.EVALUATED: frozenset(),
    Status.FAILED: frozenset(),
}

# Which optional foreign key each kind requires. The table enforces the same
# thing with a CHECK; this is what the service consults before writing.
_REFERENCE: Mapping[Kind, str | None] = {
    Kind.PRACTICE: None,
    Kind.SELF_PRACTICE: None,
    Kind.SET_STATION: "set_entry_id",
    Kind.DEBRIEF: "source_attempt_id",
    Kind.EXAM_SLOT: "slot_id",
    Kind.PEER: "peer_session_id",
}


def is_terminal(status: Status) -> bool:
    return status in TERMINAL


def transition(current: Status, target: Status) -> Status:
    if target not in _ALLOWED[current]:
        raise InvalidTransition(f"An attempt cannot go from {current} to {target}.")
    return target


def required_reference(kind: Kind) -> str | None:
    return _REFERENCE[kind]


def should_freeze(*, render_degraded: bool, already_frozen: bool) -> bool:
    """Whether this render should become the attempt's frozen definition.

    Frozen once, on the first *successful* render. Both legacy backends freeze
    unconditionally, so an unresolved station pins a generic patient prompt to
    the attempt permanently, and a debrief whose context was incomplete pins a
    prompt carrying no transcript ids — the live insights panel then stays
    empty for the whole session and every replay of it.
    """
    return not already_frozen and not render_degraded


# Where a station's patient material can live. b2c's four products spell this
# differently, and the engine's formatter accepts either.
_PATIENT_KEYS = ("patient_information", "patient_info")


def scenario_is_renderable(content: Mapping[str, Any] | None) -> bool:
    """Whether this station has enough to render a real patient.

    The engine's `ConversationPromptFormatter` substitutes `DEFAULT_STATION`
    when it cannot find usable patient material, and says so only in a log
    line. That substitution is the degradation A2 exists to catch, so it is
    detected here, before the render — inferring it afterwards would mean
    comparing rendered text against a rendering of the default, which breaks
    the moment either changes.
    """
    if not content:
        return False
    for key in _PATIENT_KEYS:
        patient = content.get(key)
        if isinstance(patient, Mapping) and any(
            str(value).strip() for value in patient.values() if not isinstance(value, (dict, list))
        ):
            return True
    return False


def definition_payload(
    *,
    attempt_id: str,
    framework_id: str,
    scenario_source: str,
    scenario_id: str,
    instructions: str,
    greeting: str | None,
    mode: str,
    policy_version: str,
    primary_model: str,
    at: datetime,
) -> dict[str, Any]:
    """Assemble what gets frozen onto the attempt.

    Shaped as `osce_assessment.contracts.AssessmentDefinition` serialises, so
    the worker can validate it and `scoring.policy_for` can read the framework
    and policy back out of it. Built here, as plain data, so the shape is
    testable without the engine installed.
    """
    return {
        "id": attempt_id,
        "version": "1",
        "framework_id": framework_id,
        "scenario_ref": {"source": scenario_source, "scenario_id": scenario_id},
        "interaction_profile": {
            "mode": mode,
            "instructions": instructions,
            "greeting": greeting,
            "tools": [],
            "tool_context": {},
            "max_tool_steps": 5,
            "runtime_hint": "pipeline",
        },
        "evaluation_policy": {
            "framework_id": framework_id,
            "primary_model": primary_model,
            "version": policy_version,
        },
        "snapshot_at": at.isoformat(),
    }


def bootstrap_definition(definition: Mapping[str, Any]) -> dict[str, Any]:
    """The definition as the worker may see it.

    `evaluation_policy` is removed: marking is the backend's business, the
    worker cannot import an evaluator, and a worker that knew how it would be
    scored could be steered by it.
    """
    profile = definition.get("interaction_profile") or {}
    if not str(profile.get("instructions") or "").strip():
        raise UnrenderableDefinition(
            "The interaction profile has no instructions; the worker would refuse this job."
        )
    return {key: value for key, value in definition.items() if key != "evaluation_policy"}


def should_store_chunk(message_id: str, seen: frozenset[str] | set[str]) -> bool:
    """Chunks repeat. The worker posts them best-effort and never reads the
    response, so the same turn can arrive more than once."""
    return message_id not in seen


def should_accept_transcript(*, already_complete: bool) -> bool:
    return not already_complete


def should_score(*, scored_versions: frozenset[str] | set[str], policy_version: str) -> bool:
    """Scoring is keyed by policy version.

    Re-running the same policy stores nothing new; scoring under a different
    one — a new org rubric, a changed model — is a new result beside the old,
    never a replacement, so a candidate's history stays readable.
    """
    return policy_version not in scored_versions
