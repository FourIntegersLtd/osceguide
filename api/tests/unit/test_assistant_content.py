"""The assistant answers from the pack, layered for the exam and the screen.

The pack is ported from b2c unchanged, so what is worth asserting here is the
layering and the filtering around it: those are what make an answer match the
screen somebody is actually looking at, and they are where a port goes wrong.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.core.settings import AppEnv, Settings, get_settings
from app.features.assistant import service_community
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
from app.features.assistant.content.prompts.onboarding import OnboardingInstructions


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


@pytest.mark.parametrize("phase", ["intro", "demo"])
def test_onboarding_answers_whatever_the_learner_says_before_returning_to_the_scene(phase: str) -> None:
    """C-54: off-script speech gets an answer, never silence; the script comes second."""
    instructions = OnboardingInstructions("How would you respond?", "I'm scared.", phase=phase)
    assert (
        instructions.get_onboarding_instructions()
        .rstrip()
        .endswith("Never stay silent after the learner speaks. If you are unsure, say so and move on.")
    )


def test_the_community_prompt_is_athena_writing_like_a_person_without_lists() -> None:
    from app.features.assistant.service_community import system_prompt

    prompt = system_prompt()

    assert "You are Athena, the OSCE Guide assistant" in prompt
    assert "Do not use bullet points, numbered lists, headings or bold" in prompt
    assert "Never say you are an AI" in prompt


def test_the_community_prompt_says_to_output_no_reply_when_the_entries_do_not_answer() -> None:
    from app.features.assistant.service_community import system_prompt

    prompt = system_prompt()

    assert "output exactly NO_REPLY" in prompt
    assert "not sure" not in prompt


def test_a_no_reply_answer_is_none_however_it_is_wrapped() -> None:
    from app.features.assistant.service_community import parse_reply

    assert [parse_reply(t) for t in ("NO_REPLY", "  no_reply.\n", "`NO_REPLY`")] == [None, None, None]
    assert parse_reply("Open Settings. NO_REPLY is not needed.") == "Open Settings. NO_REPLY is not needed."


ASSISTANT = Path(__file__).parents[2] / "app/features/assistant"
ADDRESS = r"[\w.+-]+@[\w.-]+\w|\w+ at [\w ]+ dot \w+"


@pytest.fixture
def moved_mailbox(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SUPPORT_EMAIL", "help@moved.example")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_no_pack_spells_the_support_address_out() -> None:
    """Pack prose carries placeholders: a spoken "hello at ... dot com" would escape a grep for the domain."""
    for path in sorted((ASSISTANT / "content/packs").glob("*.py")):
        assert not re.findall(ADDRESS, path.read_text(), re.IGNORECASE), path.name


def test_help_pack_answers_quote_the_configured_support_address(moved_mailbox: None) -> None:
    answers = " ".join(e.answer for e in resolve_content_pack(ClientProfile(surface="exam", exam="all")).faq)
    assert "help@moved.example" in answers
    assert "help at moved dot example" in answers
    assert "{support_email" not in answers


def test_the_community_prompt_quotes_the_configured_support_address(moved_mailbox: None) -> None:
    """The model that drafts public replies must never be handed a raw placeholder."""
    prompt = service_community.system_prompt()
    assert "help@moved.example" in prompt
    assert "help at moved dot example" in prompt
    assert "{support_email" not in prompt
    assert "{nav." not in prompt


def test_help_content_json_is_static_and_quotes_the_default_address(monkeypatch: pytest.MonkeyPatch) -> None:
    """help_content.json is not rendered: two copies, guarded against the default address only."""
    monkeypatch.delenv("SUPPORT_EMAIL", raising=False)
    default = Settings(_env_file=None, app_env=AppEnv.local).support_email
    assert default == "hello@osceguide.com"
    quoted = re.findall(ADDRESS, (ASSISTANT / "help_content.json").read_text(), re.IGNORECASE)
    assert sorted(q.lower() for q in quoted) == ["hello at osceguide dot com", "hello@osceguide.com"]
