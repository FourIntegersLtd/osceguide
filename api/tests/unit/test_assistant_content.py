"""The assistant answers from the pack, layered for the exam and the screen.

The pack is ported from b2c unchanged, so what is worth asserting here is the
layering and the filtering around it: those are what make an answer match the
screen somebody is actually looking at, and they are where a port goes wrong.
"""

from __future__ import annotations

import pytest

from app.features.assistant.content import (
    ClientProfile,
    NavItem,
    UnsupportedSurfaceError,
    packs,
    resolve_client_profile,
    resolve_content_pack,
)
from app.features.assistant.content.models import FaqEntry
from app.features.assistant.content.overlay import Overlay, OverlayError, apply
from app.features.assistant.content.prompts.faq_block import FAQ_BLOCK_HEADER, render_faq_block


def nav(*keys: str) -> tuple[NavItem, ...]:
    return tuple(NavItem(key=key, label=key.title(), path=f"/{key}") for key in keys)


def test_the_exam_decides_which_scenarios_a_newcomer_is_shown() -> None:
    """A PLAB candidate is introduced to PLAB, not to somebody else's exam."""
    sca = resolve_content_pack(ClientProfile(surface="exam", exam="sca"))
    plab = resolve_content_pack(ClientProfile(surface="exam", exam="plab"))
    assert sca.onboarding_scenes
    assert plab.onboarding_scenes
    assert sca.onboarding_scenes != plab.onboarding_scenes


@pytest.mark.parametrize("exam", sorted(packs.EXAM_OVERLAYS))
def test_every_demo_scene_can_be_played_without_voice(exam: str) -> None:
    """Text mode offers the scene's replies and then her model answer; a half-filled scene shows nothing."""
    scenes = resolve_content_pack(ClientProfile(surface="exam", exam=exam)).onboarding_scenes
    assert scenes
    for scene in scenes:
        assert len(scene.replies) >= 2, scene.question
        assert scene.model_answer.strip(), scene.question


def test_an_unknown_exam_still_answers_from_the_base_pack() -> None:
    pack = resolve_content_pack(ClientProfile(surface="exam", exam="not-an-exam"))
    assert pack.faq
    assert pack.persona.assistant_name == "Athena"


def test_an_entry_is_dropped_when_the_screen_has_no_such_place_to_go() -> None:
    """Directing somebody to a tab they do not have is worse than not answering."""
    narrow = resolve_content_pack(ClientProfile(surface="exam", exam="sca", navigation=nav("dashboard")))
    wide = resolve_content_pack(
        ClientProfile(surface="exam", exam="sca", navigation=nav("dashboard", "mocks"))
    )
    assert len(narrow.faq) < len(wide.faq)
    assert all(set(entry.requires_nav) <= {"dashboard"} for entry in narrow.faq)


def test_the_clients_own_labels_are_spoken_back() -> None:
    profile = ClientProfile(
        surface="exam",
        exam="sca",
        navigation=(NavItem(key="messages", label="Talk to us", path="/messages"),),
    )
    pack = resolve_content_pack(profile)
    assert "Talk to us" in pack.no_match_message
    assert "{nav." not in pack.no_match_message


def test_without_a_catalogue_nothing_is_filtered_and_the_defaults_fill_in() -> None:
    """Onboarding has no navigation yet; it must still get a whole pack."""
    pack = resolve_content_pack(ClientProfile(surface="exam", exam="sca"))
    assert pack.faq
    assert packs.DEFAULT_LABELS["messages"] in pack.no_match_message


def test_the_employer_surface_is_refused_rather_than_answered() -> None:
    """There is no employer product here — the employer arm is B2B exam mode."""
    with pytest.raises(UnsupportedSurfaceError):
        resolve_client_profile({"client": {"surface": "employer"}, "exam_code": "sca"})


def test_the_admin_pack_is_only_for_an_admin() -> None:
    record = {"client": {"surface": "admin"}, "exam_code": "sca"}
    assert resolve_client_profile(record).surface == "exam"
    assert resolve_client_profile({**record, "role": "admin"}).surface == "admin"


def test_the_exam_comes_from_the_account_not_the_clients_claim() -> None:
    profile = resolve_client_profile({"client": {"surface": "exam"}, "exam_code": "PLAB"})
    assert profile.exam == "plab"
    # No exam on the account means no exam's wording: the shared pack alone.
    without_exam = resolve_client_profile({"client": {}})
    assert without_exam.exam == ""
    assert resolve_content_pack(without_exam).faq


def test_an_overlay_that_targets_an_entry_nobody_has_is_a_mistake_worth_raising() -> None:
    """Silently ignoring it is how a pack keeps an answer it was meant to replace."""
    with pytest.raises(OverlayError):
        apply(packs.BASE, Overlay(remove=("no-such-entry",)))
    with pytest.raises(OverlayError):
        apply(
            packs.BASE,
            Overlay(add=(FaqEntry(id=packs.BASE.entry_ids()[0], section="s", question="q", answer="a"),)),
        )


def test_the_whole_faq_is_rendered_into_the_prompt() -> None:
    """Every entry, not a keyword-chosen handful: the model reads the list itself."""
    pack = resolve_content_pack(ClientProfile(surface="exam", exam="sca"))
    block = render_faq_block(pack)
    assert block.startswith(FAQ_BLOCK_HEADER)
    assert all(entry.question in block for entry in pack.faq)


@pytest.mark.parametrize("surface", ["exam", "admin"])
def test_help_presents_as_text_help_not_a_persona(surface: str) -> None:
    """Help is text "Help" on every surface; Athena is the clinical voice (C-38)."""
    greeting = resolve_content_pack(ClientProfile(surface=surface, exam="sca")).greetings["help"]
    assert "Athena" not in greeting
    assert greeting.startswith("Hi, this is Help.")
