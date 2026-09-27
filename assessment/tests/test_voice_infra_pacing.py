"""The clock nudges the model and never speaks for it.

The whole design rests on two properties: a mark lands in the model's context
rather than in the room, so it can never talk over the person it is listening
to; and the last mark is a note like any other, so nothing is ever cut off.
Both are asserted here rather than left to a live run.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from voice_infra.pacing import InteractionClock, PacingPlan, _spoken_duration, build_check_time_tool


class FakeChatCtx:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def copy(self) -> "FakeChatCtx":
        clone = FakeChatCtx()
        clone.messages = list(self.messages)
        return clone

    def add_message(self, role: str, content: str) -> None:
        self.messages.append((role, content))


def fake_session():
    agent = SimpleNamespace(chat_ctx=FakeChatCtx(), update_chat_ctx=AsyncMock())
    return SimpleNamespace(current_agent=agent, generate_reply=MagicMock(), say=AsyncMock()), agent


def plan(**overrides) -> PacingPlan:
    payload = {
        "total_seconds": 0.1,
        "marks": [{"at_seconds": 0.02, "note": "[Notice: first]"}, {"at_seconds": 0.05, "note": "[Notice: second]"}],
        "phases": [{"until_seconds": 0.05, "label": "history taking"}, {"until_seconds": 0.1, "label": "the close"}],
    }
    return PacingPlan.model_validate({**payload, **overrides})


def test_marks_arrive_in_order_as_context_and_the_model_is_never_made_to_speak() -> None:
    session, agent = fake_session()

    async def run() -> None:
        clock = InteractionClock(plan())
        clock.start(session)
        await asyncio.sleep(0.12)
        await clock.cancel()

    asyncio.run(run())
    notes = [call.args[0].messages[-1] for call in agent.update_chat_ctx.await_args_list]
    assert notes == [("system", "[Notice: first]"), ("system", "[Notice: second]")]
    session.generate_reply.assert_not_called()
    session.say.assert_not_awaited()


def test_cancelling_before_a_mark_lands_drops_it_quietly() -> None:
    session, agent = fake_session()

    async def run() -> None:
        clock = InteractionClock(plan())
        clock.start(session)
        await clock.cancel()
        await asyncio.sleep(0.08)

    asyncio.run(run())
    agent.update_chat_ctx.assert_not_awaited()


def test_cancelling_a_clock_that_never_started_raises_nothing() -> None:
    asyncio.run(InteractionClock(plan()).cancel())


def test_a_lost_mark_does_not_end_the_interaction() -> None:
    session, agent = fake_session()
    agent.update_chat_ctx.side_effect = RuntimeError("boom")

    async def run() -> None:
        clock = InteractionClock(plan())
        clock.start(session)
        await asyncio.sleep(0.08)
        await clock.cancel()

    asyncio.run(run())  # the RuntimeError is swallowed by apply_notice


def test_the_clock_says_nothing_until_it_starts() -> None:
    assert InteractionClock(plan()).status_text() == "This has not started yet."


def test_the_status_names_the_phase_it_is_in_and_then_the_next_one() -> None:
    session, _ = fake_session()

    async def run() -> list[str]:
        clock = InteractionClock(plan(total_seconds=0.2, marks=[]))
        clock.start(session)
        first = clock.status_text()
        await asyncio.sleep(0.07)
        return [first, clock.status_text()]

    early, later = asyncio.run(run())
    assert "history taking" in early
    assert "the close" in later


def test_past_the_end_it_says_to_finish_rather_than_to_stop() -> None:
    """Pace only: nothing here ends the interaction, not even the last mark."""
    session, _ = fake_session()

    async def run() -> str:
        clock = InteractionClock(plan(total_seconds=0.02, marks=[]))
        clock.start(session)
        await asyncio.sleep(0.05)
        return clock.status_text()

    text = asyncio.run(run())
    assert "past the time set aside" in text and "finish the point you are on" in text
    assert "Do not start anything new" in text


@pytest.mark.parametrize(("seconds", "said"), [(30, "30 sec"), (60, "1 min"), (90, "1 min 30 sec"), (720, "12 min")])
def test_durations_are_written_the_way_they_are_said(seconds, said) -> None:
    assert _spoken_duration(seconds) == said


def test_the_time_tool_is_silent_and_answers_from_the_clock() -> None:
    clock = InteractionClock(plan())
    tool = build_check_time_tool(clock)
    assert tool.info.name == "check_time"
    assert "never mention the clock" in tool.info.description
    assert asyncio.run(tool(SimpleNamespace())) == clock.status_text()


def test_the_engine_debrief_clock_is_a_plan_the_worker_accepts() -> None:
    """What platform-api sends for a debrief must validate here, or the session would refuse to start."""
    from osce_assessment.prompts import debrief_pacing_payload

    debrief = PacingPlan.model_validate(debrief_pacing_payload())
    assert debrief.total_seconds == 600
    assert [mark.at_seconds for mark in debrief.marks] == [150, 300, 480, 600]
