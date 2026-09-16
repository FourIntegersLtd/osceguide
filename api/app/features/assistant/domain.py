"""Sessions where the assistant helps someone use the product.

Distinct from an attempt: nobody is being assessed, nothing is marked, and only
one of the four kinds keeps a transcript at all.

The worker knows four types and no product vocabulary. b2c's records call one
persona `athena-doctor` while the worker calls it `consulting-doctor`; that
translation happens once, at this boundary, which is the pattern b2c already
gets right.
"""

from __future__ import annotations

from enum import StrEnum


class AssistantType(StrEnum):
    HELP = "help"
    ONBOARDING = "onboarding"
    DASHBOARD = "dashboard"
    CONSULTING_DOCTOR = "consulting-doctor"


class UnknownAssistantType(ValueError):
    pass


class UnrenderableSession(Exception):
    pass


# Legacy spellings that existing records carry.
_ALIASES = {"athena-doctor": AssistantType.CONSULTING_DOCTOR}

# Oracle: `modes.py`. Only a help session is worth keeping a transcript of —
# the others are navigation, and storing them would collect recordings of
# people's screens for nothing.
_KEEPS_TRANSCRIPT = frozenset({AssistantType.HELP})

JOINABLE_STATUSES = frozenset({"active"})


def worker_type_for(session_type: str) -> str:
    key = (session_type or "").strip().lower()
    if key in _ALIASES:
        return str(_ALIASES[key])
    try:
        return str(AssistantType(key))
    except ValueError as exc:
        raise UnknownAssistantType(f"No assistant worker handles {session_type!r}.") from exc


def keeps_transcript(session_type: str) -> bool:
    return AssistantType(worker_type_for(session_type)) in _KEEPS_TRANSCRIPT


def ensure_dispatchable(*, instructions: str) -> None:
    if not (instructions or "").strip():
        raise UnrenderableSession(
            "The assistant worker refuses a session with no instructions; render them first."
        )


def can_join(*, status: str) -> bool:
    return status in JOINABLE_STATUSES
