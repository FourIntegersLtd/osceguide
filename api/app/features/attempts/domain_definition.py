"""What is frozen onto an attempt, and what of it the worker may see.

The attempt's lifecycle rules live in `domain.py`; this is the shape of its
definition: whether a station renders to a real patient, the scenario the
worker is handed, the payload that is frozen, and the filter that keeps the
marker's half of it away from the worker. Pure functions, no I/O, checked by
the same guards as `domain.py`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from app.features.attempts.domain import UnrenderableDefinition

# Where a station's patient material can live when no template says. b2c's
# four products spell this differently, and the engine's formatter accepts
# either.
_PATIENT_KEYS = ("patient_information", "patient_info")

# Block roles the patient is built from. `examiner` and `candidate_brief` are
# excluded deliberately: a station that has only those has nothing to say as a
# patient, however full it looks.
_PATIENT_ROLES = frozenset(
    {"persona", "complaint", "instructions", "history", "medications", "social", "examination", "hidden"}
)


def scenario_is_renderable(
    content: Mapping[str, Any] | None, layout: Sequence[Mapping[str, Any]] | None = None
) -> bool:
    """Whether this station has enough to render a real patient.

    A render that produces a patient with nothing to say is the degradation A2
    exists to catch: it is served, so a session is never blocked, but it is
    never frozen, so the attempt tries again once the station is fixed.

    `layout` is the station template's block list. Without it this can only go
    on the legacy nested shapes, which is what it did for every station — so a
    station authored against a template, whose block ids are whatever its
    author chose, was always judged degraded and its definition never frozen.
    It ran and was never marked.
    """
    if not content:
        return False
    if layout:
        wanted = {
            str(block.get("id"))
            for block in layout
            if str(block.get("role") or "") in _PATIENT_ROLES and block.get("id")
        }
        return any(_has_text(content.get(block_id)) for block_id in wanted)
    for key in _PATIENT_KEYS:
        patient = content.get(key)
        if isinstance(patient, Mapping) and any(
            str(value).strip() for value in patient.values() if not isinstance(value, (dict, list))
        ):
            return True
    return False


def _has_text(value: Any) -> bool:
    """Whether a block holds anything a patient could say.

    Mirrors what the engine's formatter accepts: a string, a list of them, or
    a rich-text blob. It does not re-implement the rendering, only asks whether
    there is something rather than nothing.
    """
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple)):
        return any(_has_text(item) for item in value)
    if isinstance(value, Mapping):
        return any(_has_text(item) for item in value.values())
    return False


# Where a station records the patient's gender, across the four document shapes.
_GENDER_KEYS = ("patient_gender", "gender", "sex")


def _patient_block(content: Mapping[str, Any] | None) -> Mapping[str, Any]:
    for key in _PATIENT_KEYS:
        block = (content or {}).get(key)
        if isinstance(block, Mapping):
            return block
    return {}


def patient_gender(content: Mapping[str, Any] | None) -> str | None:
    """`male` or `female` when the station says which, else None.

    The worker picks the patient's voice from this; without it every patient
    speaks with the same default voice whatever the station says.
    """
    patient = _patient_block(content)
    for key in _GENDER_KEYS:
        value = str(patient.get(key) or (content or {}).get(key) or "").strip().lower()
        if value.startswith("m"):
            return "male"
        if value.startswith("f"):
            return "female"
    return None


def scenario_payload(
    *,
    scenario_id: str,
    scenario_source: str,
    title: str,
    content: Mapping[str, Any] | None,
    examiner_context: str | None = None,
) -> dict[str, Any]:
    """The scenario the worker is handed, shaped as `osce_assessment.contracts.Scenario`.

    Only what the worker needs: the identity, the title and the patient's
    gender. The rendered instructions already carry the case, so `raw` stays
    empty and no marking material travels with the session.

    `examiner_context` is the exception, and it is not for the worker: the
    marker reads it, and the frozen scenario is where it travels. It holds the
    expected answers a station template marks `examiner`, which the live
    persona is never shown.
    """
    return {
        "id": scenario_id,
        "source": scenario_source,
        "title": title,
        "patient_brief": {},
        "patient_gender": patient_gender(content),
        "candidate_brief": None,
        "duration_seconds": None,
        "examiner_context": examiner_context,
        "raw": {},
    }


def definition_payload(
    *,
    attempt_id: str,
    framework_id: str,
    scenario_source: str,
    scenario_id: str,
    scenario: Mapping[str, Any],
    instructions: str,
    greeting: str | None,
    mode: str,
    policy_version: str,
    primary_model: str,
    at: datetime,
    voice: str | None = None,
    rubric: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble what gets frozen onto the attempt.

    Shaped as `osce_assessment.contracts.AssessmentDefinition` serialises, so
    the worker can validate it and `jobs.policy_for` can read the framework
    and policy back out of it. Built here, as plain data, so the shape is
    testable without the engine installed.

    Two keys are ours, not the engine's: `evaluation_policy` (the marker's) and
    `scenario` (frozen beside the definition so a replay hands the worker the
    same scenario it had). `bootstrap_definition` strips both.

    The policy carries the whole `rubric` — the framework, its prompt and its
    clock — rather than an id to look one up by. Marking then needs no mutable
    row, so re-marking an attempt next year uses the wording it was assessed
    against rather than whatever the rubric says by then.
    """
    return {
        "id": attempt_id,
        "version": "1",
        "framework_id": framework_id,
        "scenario_ref": {"source": scenario_source, "scenario_id": scenario_id},
        "scenario": dict(scenario),
        "interaction_profile": {
            "mode": mode,
            "instructions": instructions,
            "voice": voice,
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
            "rubric": dict(rubric) if rubric else None,
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
    return {key: value for key, value in definition.items() if key not in _BACKEND_ONLY_KEYS}


# Frozen with the definition but not part of the engine's `AssessmentDefinition`,
# which forbids extra fields. The worker is handed the scenario separately.
_BACKEND_ONLY_KEYS = frozenset({"evaluation_policy", "scenario"})


def worker_scenario(definition: Mapping[str, Any]) -> dict[str, Any]:
    """The `Scenario` to hand the worker for this definition.

    Read from the frozen payload when it carries one. A definition frozen before
    scenarios were stored still has its `scenario_ref`, which is enough to build
    the smallest scenario the worker accepts — it used to be handed a shape the
    engine rejected outright, and no live session could start.
    """
    stored = definition.get("scenario")
    if isinstance(stored, Mapping) and stored.get("id"):
        return dict(stored)
    ref = definition.get("scenario_ref") or {}
    return {
        "id": str(ref.get("scenario_id") or definition.get("id") or ""),
        "source": str(ref.get("source") or "library"),
        "title": "",
    }


def rubric_for(definition: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """The rubric snapshot frozen onto an attempt, if it has one.

    An attempt frozen before rubrics were data has none, and cannot be marked:
    there is no framework id to guess from any more, which is the point.
    """
    policy = (definition or {}).get("evaluation_policy") or {}
    rubric = policy.get("rubric")
    return dict(rubric) if isinstance(rubric, Mapping) else None
