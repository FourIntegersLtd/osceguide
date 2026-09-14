"""Candidate matching, the join wait, and the duplicate-agent guard."""

from __future__ import annotations

import asyncio

import pytest

from voice_infra.participants import identity_matches, other_agents_present, wait_for_candidate

from _worker_fakes import FakeRoom


@pytest.mark.parametrize(
    ("identity", "ref", "expected"),
    [
        ("user-9", "user-9", True),
        ("user-9-web", "user-9", True),  # substring match, as the legacy trainee wait did
        ("user-99", "user-9", True),
        ("other", "user-9", False),
        ("agent-x", "", False),  # no ref: any non-agent counts
        ("someone", "", True),
    ],
)
def test_identity_matching(identity, ref, expected) -> None:
    assert identity_matches(identity, ref) is expected


def test_candidate_already_present_is_returned_immediately() -> None:
    room = FakeRoom()
    present = room.join("candidate-42")
    assert asyncio.run(wait_for_candidate(room, "candidate-42", timeout=0.01)) is present


def test_candidate_joining_later_resolves_the_wait_and_unhooks() -> None:
    async def scenario():
        room = FakeRoom()
        task = asyncio.create_task(wait_for_candidate(room, "candidate-42", timeout=1))
        await asyncio.sleep(0)
        room.join("agent-other")
        joined = room.join("candidate-42")
        assert await task is joined
        assert room.handlers["participant_connected"] == []

    asyncio.run(scenario())


def test_nobody_joining_times_out_and_unhooks() -> None:
    async def scenario():
        room = FakeRoom()
        with pytest.raises(asyncio.TimeoutError):
            await wait_for_candidate(room, "candidate-42", timeout=0.01)
        assert room.handlers["participant_connected"] == []

    asyncio.run(scenario())


def test_other_agents_are_reported_after_they_had_time_to_leave() -> None:
    room = FakeRoom(local_identity="agent-me")
    room.join("agent-stale")
    room.join("candidate-42")
    sleeps: list[float] = []

    async def sleep(delay: float) -> None:
        sleeps.append(delay)
        if len(sleeps) == 2:
            del room.remote_participants["agent-stale"]

    assert asyncio.run(other_agents_present(room, "agent-me", attempts=4, delay=1.5, sleep=sleep)) == []
    assert sleeps == [1.5, 1.5]


def test_other_agents_still_present_after_all_attempts_are_returned() -> None:
    room = FakeRoom(local_identity="agent-me")
    room.join("agent-stale")

    async def sleep(_: float) -> None:
        return None

    assert asyncio.run(other_agents_present(room, "agent-me", attempts=2, sleep=sleep)) == ["agent-stale"]
