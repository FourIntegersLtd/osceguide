"""A narrated line never opens with a filler: lines are written apart and played back to back."""

import pytest

from app.features.media_production.slide_narration import _parse, _parse_plan


@pytest.mark.parametrize(
    ("written", "said"),
    [
        ("Right, welcome everyone.", "Welcome everyone."),
        ("Okay... let us anchor this in a case.", "Let us anchor this in a case."),
        ("So what do we do?", "So what do we do?"),
        ("Right sided weakness matters here.", "Right sided weakness matters here."),
    ],
)
def test_an_intro_loses_its_opening_filler(written: str, said: str) -> None:
    narration = _parse(f'{{"intro": "{written}", "items": [], "callouts": []}}', [])

    assert narration is not None
    assert narration["intro"] == said


def test_a_section_card_and_the_sign_off_lose_their_opening_filler() -> None:
    slides = [{"title": "Welcome"}, {"title": "The case", "bullets": ["One"]}]
    reply = (
        '{"sections": [{"before": 2, "title": "The Problem", "line": "Right, let us see what we have."}],'
        ' "recap_intro": "Now, three things.",'
        ' "takeaways": [{"text": "a", "line": "A."}, {"text": "b", "line": "B."},'
        ' {"text": "c", "line": "C."}],'
        ' "signoff": "Well, thanks for listening."}'
    )

    plan = _parse_plan(reply, slides)

    assert plan is not None
    assert plan["sections"][0]["line"] == "Let us see what we have."
    assert plan["recap_intro"] == "Three things."
    assert plan["signoff"] == "Thanks for listening."
