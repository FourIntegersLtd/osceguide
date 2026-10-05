"""The producing line over one item's content, with a faked kit and model: what each stage changes,
what the model is asked, and what is handed over to staff."""

from __future__ import annotations

import dataclasses
from typing import Any

from app.features.media_production import script_check
from app.features.media_production.agent_loop import Limits
from app.features.media_production.produce import Kit, Production
from app.features.media_production.slide_pictures import library_credits
from tests.support.produce_kit import BUCKET, PICTURE, STORED, answering, checked, produce_kit

WRONG = "Estradiol patch 500 micrograms twice weekly"
RIGHT = "Estradiol patch 50 micrograms twice weekly"
DISPUTED = "Review in three months"
DECK: dict[str, Any] = {
    "topic": "Menopause",
    "slides": [
        {"title": "HRT", "bullets": [WRONG, "Add a progestogen if she has a womb"]},
        {"title": "The Twist", "bullets": ["She drives a school bus"]},
        {"title": "Safety net", "bullets": [DISPUTED]},
    ],
}
BRIEF = {"brief": {"brief": "A deck on HRT.", "source_text": "Mrs X, 52, hot flushes. HRT."}}
LIBRARY = sorted(library_credits())[0]
# The model gives slide 1 a bundled picture and searches for the others, picking the first found.
PICTURED = {
    "choose": [{"slides": [{"slide": 1, "library": LIBRARY}, {"slide": 2, "search": "school bus"}]}],
    "pick": [{"picture": 1}, {"picture": 1}],
}


async def produced(
    answers: dict[str, list[dict[str, Any]]], kit: Kit | None = None, **checks: Any
) -> tuple[Production, Any, Any, list[tuple[str, str]], list[tuple[str, str]]]:
    """A deck produced from the brief: the production, how the run ended, the kit's record, the
    questions the model was asked and the steps logged."""
    made_kit, record = produce_kit(DECK, **checks)
    turn, asked = answering(answers, tokens=10)
    made = Production(kind="slide_deck", title="Menopause", content={"review": BRIEF}, kit=kit or made_kit)
    steps: list[tuple[str, str]] = []

    async def on_step(tool: str, text: str, tokens: int) -> bool:
        steps.append((tool, text))
        made.log(tool, text, tokens)
        return True

    result = await made.produce(turn, Limits(), on_step)
    made.ended(result)
    return made, result, record, asked, steps


async def test_a_deck_is_drafted_pictured_checked_ruled_and_scripted_in_that_order_once() -> None:
    answers = {**PICTURED, "rule": [{"decision": "accept", "old": WRONG, "new": RIGHT, "reason": "NICE."}]}
    made, result, record, asked, steps = await produced(answers, wrong={WRONG: RIGHT})

    assert (result.ended, result.tokens) == ("finished", 40)
    assert [tool for tool, _ in steps] == [
        "write_draft",
        "choose_pictures",
        "set_picture",
        "set_picture",
        "check_facts",
        "rule_claim",
        "write_script",
        "finish",
    ]
    assert [tool for tool, _ in asked] == ["choose", "pick", "pick", "rule"]
    assert record.checks == 1
    assert record.searched == ["school bus", "Safety net"]
    slides = made.content["slides"]
    assert [slide["image_urls"] for slide in slides] == [[f"{BUCKET}{LIBRARY}"], [STORED], [STORED]]
    assert slides[1]["image_credits"] == [
        {"author": PICTURE.author, "licence": PICTURE.licence, "source": PICTURE.page}
    ]
    assert slides[0]["bullets"][0] == RIGHT
    [claim] = made.content["review"]["facts"]["claims"]
    assert (claim["decision"], claim["by"], claim["swap"]) == (
        "accepted",
        "agent",
        {"from": WRONG, "to": RIGHT},
    )
    assert made.content["review"]["run"]["open"] == [
        "Added (for sign-off): She drives a school bus",
        f"Corrected (slide 1, claim-1): {WRONG!r} -> {RIGHT!r}",
    ]
    assert made.content["review"]["run"]["summary"] == (
        "Drafted the slide deck 'Menopause' in 3 slides, 3 with a picture. Checked 1 claims "
        "(1 contradicted); corrected 1 and dismissed 0. Script of about 31 words, checked and not voiced."
    )


async def test_the_draft_is_asked_for_the_deck_shape_and_takes_only_the_diagnosis_from_the_source() -> None:
    _, _, record, _, _ = await produced(PICTURED)

    [prompt] = record.drafts
    assert prompt.startswith("A deck on HRT.\n\nWrite 15 to 17 slides in this order")
    assert "never a welcome" in prompt and "The Twist" in prompt
    assert "telephone call, never video" in prompt
    assert "Take only the diagnosis and its relevant management" in prompt
    assert prompt.endswith("Source case:\nMrs X, 52, hot flushes. HRT.")


async def test_a_dismissed_flag_leaves_the_text_and_is_listed_with_its_reason() -> None:
    answers = {**PICTURED, "rule": [{"decision": "dismiss", "reason": "Three months is NICE's review."}]}
    made, _, _, _, _ = await produced(answers, disputed=(DISPUTED,))

    assert made.content["slides"][2]["bullets"] == [DISPUTED]
    [claim] = made.content["review"]["facts"]["claims"]
    assert (claim["decision"], claim["by"]) == ("dismissed", "agent")
    assert (
        f"Dismissed (slide 3, claim-1): {DISPUTED} Because: Three months is NICE's review."
        in made.content["review"]["run"]["open"]
    )


async def test_a_claim_the_model_does_not_rule_on_or_whose_words_are_gone_is_left_for_staff() -> None:
    answers = {
        **PICTURED,
        "rule": [{"decision": "accept", "old": "not in the deck", "new": "x", "reason": "r"}],
    }
    made, result, _, _, steps = await produced(answers, wrong={WRONG: RIGHT}, disputed=(DISPUTED,))

    assert result.ended == "finished"
    assert ("rule_claim", "claim-1: 'not in the deck' is not in the text, left for staff.") in steps
    assert ("rule_claim", "claim-2: no ruling, left for staff.") in steps
    assert made.content["slides"][0]["bullets"][0] == WRONG
    assert made.content["review"]["run"]["open"][1:] == [
        f"Contradicted, not fixed (slide 1, claim-1): {WRONG}",
        f"The sources disagree (slide 3, claim-2): {DISPUTED}",
    ]


async def test_a_slide_whose_pictures_do_not_fit_is_searched_once_more_then_listed() -> None:
    answers = {**PICTURED, "pick": [{"picture": 0, "search": "bus depot"}, {"picture": 0}, {"picture": 1}]}
    made, _, record, _, steps = await produced(answers)

    assert sorted(record.searched) == ["Safety net", "bus depot", "school bus"]
    assert ("set_picture", "Slide 2: none of the pictures fit.") in steps
    assert made.content["slides"][1].get("image_urls") is None
    assert "Slides without a picture: 2." in made.content["review"]["run"]["open"]


async def test_the_script_is_read_through_and_only_exact_edits_that_keep_the_asides_are_applied() -> None:
    kit, _ = produce_kit(DECK)
    issue = {
        "part": "slide",
        "slide": 3,
        "line": 2,
        "kind": "unsourced",
        "quote": "three",
        "why": "Say when.",
    }

    async def write_script(content: dict[str, Any], rewrite: bool) -> dict[str, Any]:
        written = await kit.write_script(content, rewrite)
        written["slides"][2]["narration"]["items"] = ["Review in three months [chuckles] , then yearly."]
        return checked(written, [issue])

    edits = [
        {"old": "[chuckles] , then", "new": "[chuckles], then"},
        {"old": " a ", "new": " the "},
        {"old": "months [chuckles]", "new": "months"},
    ]
    answers = {**PICTURED, "edit": [{"edits": edits}]}
    made, _, _, asked, steps = await produced(
        answers, kit=dataclasses.replace(kit, write_script=write_script)
    )

    assert made.content["slides"][2]["narration"]["items"] == [
        "Review in three months [chuckles], then yearly."
    ]
    logged = dict(steps)
    assert logged["edit_script"] == (
        "1 edit(s) applied.\nNot applied: ' a ' is in the script 3 times"
        "\nNot applied: 'months [chuckles]' would drop an aside"
    )
    assert logged["check_script"] == "Script checked again: 0 flagged."
    [opening] = [opening for tool, opening in asked if tool == "edit"]
    assert "- slide 3, unsourced: Say when. ('three')" in opening
    assert "- A space before punctuation in: 'Review in three months [chuckles] , then yearly.'" in opening
    assert made.content["review"]["run"]["outcome"] == "finished"


async def test_a_run_staff_stop_ends_after_the_step_it_is_on() -> None:
    kit, record = produce_kit(DECK)
    turn, asked = answering(PICTURED, tokens=10)
    made = Production(kind="slide_deck", title="Menopause", content={"review": BRIEF}, kit=kit)

    async def stop(tool: str, text: str, tokens: int) -> bool:
        return False

    result = await made.produce(turn, Limits(), stop)

    assert (result.ended, asked, record.checks) == ("stopped", [], 0)
    assert len(made.content["slides"]) == 3


async def test_a_summary_has_its_dialogue_edited_in_place_and_no_pictures() -> None:
    kit, _ = produce_kit({"body_md": "HRT relieves flushes.", "red_flags": ["Bleeding"]})

    async def write_script(content: dict[str, Any], rewrite: bool) -> dict[str, Any]:
        script = "Ben: Right , HRT relieves flushes.\n\nMichelle: [laughs] It does."
        return {
            **content,
            "script": script,
            "review": {**content["review"], "script": {"lines": [], "issues": []}},
        }

    async def check_script(content: dict[str, Any]) -> dict[str, Any]:
        lines = script_check.spoken_lines("summary", content)
        return {**content, "review": {**content["review"], "script": {"lines": lines, "issues": []}}}

    turn, asked = answering({"edit": [{"edits": [{"old": "Right , HRT", "new": "HRT"}]}]}, tokens=10)
    made = Production(
        kind="summary",
        title="Menopause",
        content={"review": BRIEF},
        kit=dataclasses.replace(kit, write_script=write_script, check_script=check_script),
    )

    async def going(tool: str, text: str, tokens: int) -> bool:
        return True

    result = await made.produce(turn, Limits(), going)

    assert result.ended == "finished"
    assert [tool for tool, _ in asked] == ["edit"]
    assert made.content["script"] == "Ben: HRT relieves flushes.\n\nMichelle: [laughs] It does."
