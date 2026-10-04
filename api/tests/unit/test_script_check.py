"""The script check against a scripted second reader: what it flags, what it corrects, what it leaves."""

from __future__ import annotations

import json
from typing import Any

from app.core.settings import get_settings
from app.features.media_production.script_check import (
    check_deck,
    is_checked,
    prepare_podcast,
    rule_hints,
    spoken_lines,
)

SOURCE = "Kwame Mensah, 46, head chef. Home monitor average 152/96. Review by telephone call appointment."
WRONG = "[chuckles] Then Jack's monitor averaged one fifty-two over ninety-six."
RIGHT = "[chuckles] Then Kwame's monitor averaged one fifty-two over ninety-six."


def deck() -> dict[str, Any]:
    return {
        "title": "New hypertension",
        "slides": [
            {
                "title": "Kwame's readings",
                "bullets": ["Home average 152 over 96"],
                "source_notes": SOURCE,
                "narration": {
                    "intro": "Here is the reading that matters.",
                    "items": [WRONG],
                    "callouts": [None],
                },
            }
        ],
        "presentation": {
            "sections": [],
            "recap_intro": "Three things to take away.",
            "takeaways": [
                {"text": "Confirm at home", "line": "Confirm the diagnosis at home."},
                {"text": "Stage it", "line": "Stage it before you treat it."},
                {"text": "Follow up", "line": "Follow up by telephone."},
            ],
            "signoff": "That is new hypertension.",
        },
    }


def reader(found: dict[str, list[dict[str, Any]]]):  # type: ignore[no-untyped-def]
    """A second reader that reports `found[needle]` for a prompt whose lines contain `needle`."""

    def complete(prompt: str) -> str:
        lines = prompt.split("The lines, numbered:")[1].split("A rule-based pass")[0]
        for needle, issues in found.items():
            if needle in lines:
                return json.dumps({"issues": issues})
        return json.dumps({"issues": []})

    return complete


JACK = {
    "line": 2,
    "kind": "name",
    "quote": "Jack's monitor",
    "why": "The patient is Kwame.",
    "fix": "Then Kwame's monitor averaged one fifty-two over ninety-six.",
}


def test_the_rules_see_a_stray_name_a_stray_number_a_video_consultation_and_a_filler() -> None:
    lines = [
        "[chuckles] Then Jack's monitor averaged 152 over 96.",
        "Book a video consultation in 4 weeks.",
        "So, that is stage two.",
    ]

    hints = rule_hints(lines, SOURCE, SOURCE)

    assert [(hint["line"], hint["kind"], hint["quote"]) for hint in hints] == [
        (1, "name", "Jack"),
        (2, "number", "4"),
        (2, "rule", "video consultation"),
        (3, "rule", "So"),
    ]


def test_a_faithful_line_raises_nothing() -> None:
    assert rule_hints(["On Monday, Kwame's monitor averaged 152 over 96."], SOURCE, SOURCE) == []


def test_a_line_written_this_run_is_corrected_and_keeps_its_audio_tag() -> None:
    checked = check_deck(reader({"Jack": [JACK]}), deck(), written=frozenset({1}), plan_written=False)

    slide = checked["slides"][0]
    assert slide["narration"]["items"] == [RIGHT]
    assert slide["speaker_notes"] == (
        "Here is the reading that matters.\n\nThen Kwame's monitor averaged one fifty-two over ninety-six."
    )
    script = checked["review"]["script"]
    assert script["issues"] == []
    assert script["changes"] == [
        {
            "part": "slide",
            "slide": 1,
            "line": 2,
            "before": WRONG,
            "after": RIGHT,
            "kind": "name",
            "why": "The patient is Kwame.",
        }
    ]
    assert is_checked("slide_deck", checked)


def test_a_line_somebody_edited_is_reported_and_left_as_it_is() -> None:
    checked = check_deck(reader({"Jack": [JACK]}), deck(), written=frozenset(), plan_written=False)

    assert checked["slides"][0]["narration"]["items"] == [WRONG]
    script = checked["review"]["script"]
    assert script["changes"] == []
    assert [(issue["part"], issue["slide"], issue["line"], issue["quote"]) for issue in script["issues"]] == [
        ("slide", 1, 2, "Jack's monitor")
    ]


def test_a_reader_that_does_not_answer_leaves_the_rule_findings() -> None:
    checked = check_deck(lambda prompt: "I cannot help", deck(), written=frozenset({1}), plan_written=True)

    script = checked["review"]["script"]
    assert [(issue["slide"], issue["kind"], issue["quote"]) for issue in script["issues"]] == [
        (1, "name", "Jack")
    ]
    assert script["changes"] == []


def test_a_deck_is_no_longer_checked_once_a_line_changes() -> None:
    checked = check_deck(reader({}), deck(), written=frozenset(), plan_written=False)
    assert is_checked("slide_deck", checked)

    checked["slides"][0]["narration"]["intro"] = "Something nobody has read."

    assert not is_checked("slide_deck", checked)


def test_a_deck_with_an_unwritten_slide_is_not_checked_and_speaks_nothing() -> None:
    content = deck()
    del content["slides"][0]["narration"]

    assert spoken_lines("slide_deck", content) == []
    assert not is_checked("slide_deck", content)


def test_a_podcast_script_already_written_is_checked_but_not_rewritten() -> None:
    script = "Ben: Jack is a head chef.\n\nMichelle: His home average was 152 over 96."
    wrong = {
        "line": 1,
        "kind": "name",
        "quote": "Jack",
        "why": "He is Kwame.",
        "fix": "Kwame is a head chef.",
    }

    checked = prepare_podcast(
        get_settings(),
        kind="podcast",
        title="New hypertension",
        content={"body_md": SOURCE, "script": script},
        rewrite=False,
        complete=reader({"Jack": [wrong]}),
    )

    assert checked["script"] == script
    review = checked["review"]["script"]
    assert review["lines"] == ["Ben: Jack is a head chef.", "Michelle: His home average was 152 over 96."]
    assert [(issue["part"], issue["line"], issue["fix"]) for issue in review["issues"]] == [
        ("script", 1, "Kwame is a head chef.")
    ]
    assert is_checked("podcast", checked)
