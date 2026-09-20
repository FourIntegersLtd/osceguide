"""Which worker serves a session, and where it runs.

Two families of LiveKit worker exist — the assessment worker that plays a
patient or a tutor, and the assistant worker that helps someone use the product.
A session type belongs to exactly one, and one setting per family decides
whether it runs on LiveKit Cloud or our own deployment.

Ported from `b2c/shared/services/livekit_agent_routing.py`, which both backends
carry near-identical copies of.
"""

from __future__ import annotations

from enum import StrEnum


class Family(StrEnum):
    ASSESSMENT = "assessment"
    ASSISTANT = "assistant"


class Mode(StrEnum):
    SELF_HOSTED = "self-hosted"
    LIVEKIT_CLOUD = "livekit-cloud"


class UnknownSessionType(ValueError):
    """A session type belonging to no worker family."""


class InvalidRoutingMode(ValueError):
    """A routing mode that is neither canonical nor a known alias."""


ASSESSMENT_TYPES = frozenset({"conversation", "admin-test", "debrief"})
ASSISTANT_TYPES = frozenset({"help", "onboarding", "dashboard", "consulting-doctor"})

# Spellings that deployed configmaps still carry. Kept because dropping them
# would not fail — it would route live traffic to the other deployment on the
# next deploy, which is far worse than an error.
_MODE_ALIASES = {
    "all-cloud": Mode.LIVEKIT_CLOUD,
    "cloud": Mode.LIVEKIT_CLOUD,
    "all-railway": Mode.SELF_HOSTED,
    "railway": Mode.SELF_HOSTED,
}


def family_for(session_type: str) -> Family:
    key = (session_type or "").strip().lower()
    if key in ASSESSMENT_TYPES:
        return Family.ASSESSMENT
    if key in ASSISTANT_TYPES:
        return Family.ASSISTANT
    raise UnknownSessionType(
        f"No worker family for session type {session_type!r}. "
        "Defaulting would dispatch a patient simulation to the help worker."
    )


def normalize_mode(raw: str | None) -> Mode:
    """Resolve a configured mode.

    Empty means self-hosted: our own capacity, not metered Cloud. An
    unrecognised value is an error rather than a default, because silently
    picking one is how a deploy sends every session to the wrong place.
    """
    key = (raw or "").strip().lower()
    if not key:
        return Mode.SELF_HOSTED
    if key in _MODE_ALIASES:
        return _MODE_ALIASES[key]
    try:
        return Mode(key)
    except ValueError as exc:
        raise InvalidRoutingMode(f"Unknown routing mode {raw!r}") from exc


def resolve_mode(configured: Mode, *, cloud_slots_free: bool) -> Mode:
    """Where this session actually runs.

    Cloud concurrency is metered and shared across products, so past the cap we
    serve from our own workers rather than refusing. The overflow is one-way:
    a self-hosted family never spills onto Cloud, because doing so unasked is a
    bill rather than a fallback.
    """
    if configured is Mode.LIVEKIT_CLOUD and not cloud_slots_free:
        return Mode.SELF_HOSTED
    return configured


def agent_name(family: Family, mode: Mode, *, namespace: str = "") -> str:
    prefix = namespace.strip()
    name = f"{family}-{mode}"
    return f"{prefix}-{name}" if prefix else name


def room_name_for(attempt_id: str) -> str:
    """One room per attempt.

    b2c used `unified_{uuid4}` and made it the attempt id as well; here the
    attempt already has an identity, so the room is derived from it and the
    name says which attempt a stray room belongs to.
    """
    return f"attempt_{attempt_id}"
