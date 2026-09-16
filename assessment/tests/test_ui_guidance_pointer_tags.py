"""Pointer tags the model writes inline, removed before the words are spoken."""

from __future__ import annotations

import asyncio
from typing import Any

from livekit_assistant_worker.ui_guidance.pointer_tags import PointerTag, strip_pointer_tags


def _run(chunks: list[Any]) -> tuple[str, list[PointerTag]]:
    seen: list[PointerTag] = []

    async def source():
        for chunk in chunks:
            yield chunk

    async def drain() -> list[Any]:
        return [piece async for piece in strip_pointer_tags(source(), seen.append)]

    pieces = asyncio.run(drain())
    return "".join(str(p) for p in pieces), seen


def test_a_tag_is_taken_out_and_its_pointer_reported() -> None:
    spoken, pointers = _run(["[POINT:840,210:AI Practice] AI Practice, tap it."])

    # The model opens with the tag, so the space that separated it must go too —
    # it would otherwise head the spoken line and the transcript.
    assert spoken == "AI Practice, tap it."
    assert pointers == [PointerTag(x=840.0, y=210.0, label="AI Practice")]


def test_a_tag_split_across_chunks_is_still_one_tag() -> None:
    """The stream arrives a few tokens at a time, so this is the normal case."""
    spoken, pointers = _run(["Tap ", "[POI", "NT:84", "0,21", "0:AI Pr", "actice]", " now."])

    assert spoken == "Tap now.", "the tag's separating space must not be left doubled"
    assert pointers == [PointerTag(x=840.0, y=210.0, label="AI Practice")]


def test_several_tags_in_one_reply_each_fire() -> None:
    spoken, pointers = _run(["[POINT:1,2:First]one[POINT:3,4:Second]two"])

    assert spoken == "onetwo"
    assert [p.label for p in pointers] == ["First", "Second"]


def test_ordinary_brackets_are_spoken_as_written() -> None:
    spoken, pointers = _run(["an [array] of ", "things"])

    assert spoken == "an [array] of things" and pointers == []


def test_a_malformed_tag_is_spoken_rather_than_swallowed() -> None:
    """Better an odd sentence than a silently truncated one."""
    spoken, pointers = _run(["see [POINT:abc] here"])

    assert spoken == "see [POINT:abc] here" and pointers == []


def test_an_unclosed_tag_at_the_end_of_the_stream_is_released() -> None:
    spoken, pointers = _run(["trailing [POINT:9,9"])

    assert spoken == "trailing [POINT:9,9" and pointers == []


def test_a_stray_bracket_does_not_swallow_the_rest_of_the_sentence() -> None:
    long_tail = "x" * 200
    spoken, _ = _run(["[" + long_tail])

    assert spoken == "[" + long_tail


def test_chunks_without_tags_are_passed_through_untouched() -> None:
    """A TimedString keeps its word timings on every turn that points at nothing."""

    class Timed(str):
        start_time = 1.5

    async def source():
        yield Timed("Nothing to point at.")

    async def drain():
        return [piece async for piece in strip_pointer_tags(source())]

    pieces = asyncio.run(drain())

    assert isinstance(pieces[0], Timed) and pieces[0].start_time == 1.5


def test_a_tag_with_no_label_still_places_the_pointer() -> None:
    spoken, pointers = _run(["x[POINT:5,6]y"])

    assert spoken == "xy" and pointers == [PointerTag(x=5.0, y=6.0, label="")]


def test_a_tag_between_two_words_leaves_exactly_one_space() -> None:
    assert _run(["the [POINT:1,2:Tab] Tab is there"])[0] == "the Tab is there"


def test_words_that_never_had_a_space_are_not_joined_differently() -> None:
    assert _run(["one[POINT:1,2:A]two"])[0] == "onetwo"


def test_the_real_shape_a_model_produces() -> None:
    """Taken verbatim from a live turn against claude-haiku-4-5."""
    spoken, pointers = _run(["[POINT:47,135:AI Practice] AI Practice, tap it, then say next."])

    assert spoken == "AI Practice, tap it, then say next."
    assert pointers == [PointerTag(x=47.0, y=135.0, label="AI Practice")]
