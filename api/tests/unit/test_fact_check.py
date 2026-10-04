"""The fact check with a scripted model, guideline library and web search: who is asked, and the verdict."""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.core.ports import GuidelinePassage, WebAnswer
from app.features.media_production.fact_check import check_facts
from tests.support.fakes import FakeGuidelineIndex, FakeGuidelineWeb

DECK = {
    "slides": [
        {"title": "The patient", "bullets": ["Head chef, 46"]},
        {"title": "Staging", "bullets": ["Stage 2 is a clinic reading of 150/95 or more"]},
    ]
}
CLAIM = "Stage 2 is a clinic reading of 150/95 or more"
QUESTION = "What clinic blood pressure defines stage 2 hypertension?"
NG136 = GuidelinePassage(
    source="NICE NG136",
    text="Stage 2 hypertension: clinic blood pressure of 160/100 mmHg or higher.",
    score=0.9,
    section="1.2 Diagnosing hypertension",
    page=12,
)
WEB = WebAnswer(
    answer="Stage 2 is a clinic reading of 160/100 or more [1].",
    references=(
        {"title": "NICE CKS Hypertension", "url": "https://cks.nice.org.uk/hypertension", "quotes": []},
    ),
)


def model(library: dict[str, Any] | None = None, web: dict[str, Any] | None = None):  # type: ignore[no-untyped-def]
    """A model that lists the one claim, and gives `library` and `web` as its two verdicts."""

    def complete(prompt: str) -> str:
        if "List the clinical claims" in prompt:
            return json.dumps({"claims": [{"section": 2, "claim": CLAIM, "question": QUESTION}]})
        return json.dumps(library if "guideline library" in prompt else web)

    return complete


async def claims(complete, guidelines, web) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
    facts = await check_facts(
        kind="slide_deck",
        title="New hypertension",
        content=DECK,
        guidelines=guidelines,
        web=web,
        complete=complete,
    )
    return facts["claims"]


@pytest.mark.asyncio
async def test_a_claim_the_library_supports_never_reaches_the_web() -> None:
    library, web = FakeGuidelineIndex([NG136]), FakeGuidelineWeb(WEB)
    verdict = {"verdict": "supported", "evidence": 1, "quote": "160/100 mmHg or higher", "why": "Same."}

    found = await claims(model(library=verdict), library, web)

    assert library.searches == [(QUESTION, 5, True)]
    assert web.questions == []
    assert found == [
        {
            "id": "claim-1",
            "slide": 2,
            "claim": CLAIM,
            "verdict": "supported",
            "why": "Same.",
            "checked": ["guidelines"],
            "evidence": [
                {
                    "kind": "guideline",
                    "source": "NICE NG136",
                    "section": "1.2 Diagnosing hypertension",
                    "page": 12,
                    "url": None,
                    "quote": "160/100 mmHg or higher",
                }
            ],
            "suggestion": None,
        }
    ]


@pytest.mark.asyncio
async def test_a_claim_the_library_is_silent_on_is_put_to_the_web_once() -> None:
    library, web = FakeGuidelineIndex([NG136]), FakeGuidelineWeb(WEB)
    silent = {"verdict": "not_found", "evidence": None, "why": "Not covered."}
    backed = {"verdict": "supported", "evidence": 1, "quote": "160/100 or more", "why": "CKS agrees."}

    found = await claims(model(library=silent, web=backed), library, web)

    assert web.questions == [QUESTION]
    assert (found[0]["verdict"], found[0]["checked"]) == ("supported", ["guidelines", "web"])
    assert found[0]["evidence"] == [
        {
            "kind": "web",
            "source": "NICE CKS Hypertension",
            "section": "",
            "page": None,
            "url": "https://cks.nice.org.uk/hypertension",
            "quote": "160/100 or more",
        }
    ]


@pytest.mark.asyncio
async def test_a_contradiction_comes_back_as_an_exact_replacement() -> None:
    wrong = {
        "verdict": "contradicted",
        "evidence": 1,
        "quote": "160/100 mmHg or higher",
        "why": "NG136 says 160/100.",
        "old": "150/95",
        "new": "160/100",
    }

    found = await claims(model(library=wrong), FakeGuidelineIndex([NG136]), FakeGuidelineWeb(None))

    assert (found[0]["verdict"], found[0]["checked"]) == ("contradicted", ["guidelines"])
    assert found[0]["suggestion"] == {"old": "150/95", "new": "160/100"}


@pytest.mark.asyncio
async def test_a_replacement_for_words_that_are_not_on_the_slide_is_advice_only() -> None:
    wrong = {"verdict": "contradicted", "evidence": 1, "why": "No.", "old": "150 over 95", "new": "160/100"}

    found = await claims(model(library=wrong), FakeGuidelineIndex([NG136]), None)

    assert found[0]["suggestion"] == {"old": None, "new": "160/100"}


@pytest.mark.asyncio
async def test_the_library_and_the_web_disagreeing_is_a_conflict() -> None:
    wrong = {
        "verdict": "contradicted",
        "evidence": 1,
        "why": "NG136 says 160/100.",
        "old": "150/95",
        "new": "160/100",
    }
    backed = {"verdict": "supported", "evidence": 1, "why": "The web agrees with the slide."}

    found = await claims(model(library=wrong, web=backed), FakeGuidelineIndex([NG136]), FakeGuidelineWeb(WEB))

    assert found[0]["verdict"] == "conflict"


@pytest.mark.asyncio
async def test_with_nothing_to_ask_a_claim_is_not_checked_rather_than_a_failure() -> None:
    found = await claims(model(), None, None)

    assert [(claim["verdict"], claim["checked"], claim["evidence"]) for claim in found] == [
        ("not_checked", [], [])
    ]
