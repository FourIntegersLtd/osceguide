"""Which worker serves a session, and what a token may do.

Ported from `b2c livekit_agent_routing.py` and `b2b livekit/token.py`. The mode
aliases are kept because deployed configmaps still carry the old spellings, and
a rename that silently routes to the wrong agent is the worst kind.
"""

from __future__ import annotations

import pytest

from app.features.voice import domain

# --------------------------------------------------------------------------
# Worker families
# --------------------------------------------------------------------------


@pytest.mark.parametrize("session_type", ["conversation", "admin-test", "debrief"])
def test_assessment_session_types(session_type: str) -> None:
    assert domain.family_for(session_type) is domain.Family.ASSESSMENT


@pytest.mark.parametrize("session_type", ["help", "onboarding", "dashboard", "consulting-doctor"])
def test_assistant_session_types(session_type: str) -> None:
    assert domain.family_for(session_type) is domain.Family.ASSISTANT


def test_an_unknown_session_type_is_refused_rather_than_defaulted() -> None:
    """Defaulting would dispatch a patient simulation to the help worker."""
    with pytest.raises(domain.UnknownSessionType):
        domain.family_for("nonsense")


def test_the_two_families_do_not_overlap() -> None:
    assert not (domain.ASSESSMENT_TYPES & domain.ASSISTANT_TYPES)


# --------------------------------------------------------------------------
# Routing mode
# --------------------------------------------------------------------------


@pytest.mark.parametrize("raw", ["self-hosted", "SELF-HOSTED", "  self-hosted "])
def test_self_hosted_is_the_canonical_mode(raw: str) -> None:
    assert domain.normalize_mode(raw) is domain.Mode.SELF_HOSTED


@pytest.mark.parametrize("alias", ["all-cloud", "cloud"])
def test_legacy_cloud_aliases_still_resolve(alias: str) -> None:
    """Deployed configmaps carry these spellings; dropping them would route
    live traffic to the wrong agent on the next deploy."""
    assert domain.normalize_mode(alias) is domain.Mode.LIVEKIT_CLOUD


@pytest.mark.parametrize("alias", ["all-railway", "railway"])
def test_legacy_self_hosted_aliases_still_resolve(alias: str) -> None:
    assert domain.normalize_mode(alias) is domain.Mode.SELF_HOSTED


def test_an_empty_mode_falls_back_to_self_hosted() -> None:
    """The safe default: our own capacity rather than metered Cloud."""
    assert domain.normalize_mode("") is domain.Mode.SELF_HOSTED
    assert domain.normalize_mode(None) is domain.Mode.SELF_HOSTED


def test_an_unrecognised_mode_is_an_error_not_a_default() -> None:
    with pytest.raises(domain.InvalidRoutingMode):
        domain.normalize_mode("somewhere-else")


# --------------------------------------------------------------------------
# Agent names
# --------------------------------------------------------------------------


def test_the_agent_name_pairs_family_with_mode() -> None:
    assert domain.agent_name(domain.Family.ASSESSMENT, domain.Mode.SELF_HOSTED) == "assessment-self-hosted"
    assert domain.agent_name(domain.Family.ASSISTANT, domain.Mode.LIVEKIT_CLOUD) == "assistant-livekit-cloud"


# --------------------------------------------------------------------------
# Rooms and capacity
# --------------------------------------------------------------------------


def test_a_room_name_is_unique_per_attempt() -> None:
    first = domain.room_name_for("11111111-1111-1111-1111-111111111111")
    second = domain.room_name_for("22222222-2222-2222-2222-222222222222")
    assert first != second
    assert first.startswith("attempt_")


def test_cloud_overflows_to_self_hosted_when_full() -> None:
    """Cloud concurrency is metered and shared; past the cap we serve from our
    own workers rather than refusing the session."""
    assert domain.resolve_mode(domain.Mode.LIVEKIT_CLOUD, cloud_slots_free=False) is domain.Mode.SELF_HOSTED
    assert domain.resolve_mode(domain.Mode.LIVEKIT_CLOUD, cloud_slots_free=True) is domain.Mode.LIVEKIT_CLOUD


def test_self_hosted_never_overflows_to_cloud() -> None:
    """Overflow is one-way: spilling onto metered Cloud without being asked to
    is a bill, not a fallback."""
    assert domain.resolve_mode(domain.Mode.SELF_HOSTED, cloud_slots_free=True) is domain.Mode.SELF_HOSTED
