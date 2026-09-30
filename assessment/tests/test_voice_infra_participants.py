"""Candidate matching, the join wait, and the duplicate-agent guard."""

from __future__ import annotations

import asyncio

import pytest

from voice_infra.participants import (
    Outranked,
    agents_with_priority,
    find_candidate,
    identity_matches,
    outranks,
    wait_for_candidate,
)

from _worker_fakes import FakeRoom, participant


@pytest.mark.parametrize(
    ("identity", "ref", "expected"),
    [
        ("user-9", "user-9", True),
        ("user-9-web", "user-9", True),  # substring match, as the legacy trainee wait did
        ("user-99", "user-9", True),
        ("other", "user-9", False),
        ("agent-user-9", "user-9", False),  # an agent is never the candidate
        ("agent-x", "", False),
        ("someone", "", False),  # no ref: nobody is chosen
    ],
)
def test_identity_matching(identity, ref, expected) -> None:
    assert identity_matches(identity, ref) is expected


def test_exact_identity_wins_over_a_substring_match() -> None:
    """A shared room: a sibling id and a suffixed id are present alongside the real candidate."""
    people = [participant("user-99"), participant("supervisor"), participant("user-9"), participant("user-9-web")]
    assert find_candidate(people, "user-9").identity == "user-9"
    assert find_candidate(reversed(people), "user-9").identity == "user-9"


def test_substring_match_is_used_only_without_an_exact_one() -> None:
    assert find_candidate([participant("supervisor"), participant("user-9-web")], "user-9").identity == "user-9-web"
    assert find_candidate([participant("supervisor")], "user-9") is None
    assert find_candidate([participant("someone")], "") is None


def test_candidate_already_present_is_returned_immediately() -> None:
    room = FakeRoom()
    present = room.join("candidate-42")
    assert asyncio.run(wait_for_candidate(room, "candidate-42", timeout=0.01)) is present


def test_present_exact_candidate_is_preferred_over_present_lookalikes() -> None:
    room = FakeRoom()
    room.join("candidate-421")
    exact = room.join("candidate-42")
    assert asyncio.run(wait_for_candidate(room, "candidate-42", timeout=0.01)) is exact


def test_nobody_is_chosen_without_a_reference() -> None:
    room = FakeRoom()
    room.join("someone")
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(wait_for_candidate(room, "", timeout=0.01))


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


def test_an_agent_on_its_way_out_is_waited_for_rather_than_yielded_to() -> None:
    """A stale agent from a finished job is leaving; this one should not give up the room to it."""
    room = FakeRoom(local_identity="agent-me")
    room.join("agent-earlier")  # outranks this one, so it would otherwise hold the room
    room.join("candidate-42")
    sleeps: list[float] = []

    async def sleep(delay: float) -> None:
        sleeps.append(delay)
        if len(sleeps) == 2:
            del room.remote_participants["agent-earlier"]

    assert asyncio.run(agents_with_priority(room, "agent-me", attempts=4, delay=1.5, sleep=sleep)) == []
    assert sleeps == [1.5, 1.5]


def test_an_agent_that_will_not_leave_and_outranks_this_one_keeps_the_room() -> None:
    room = FakeRoom(local_identity="agent-me")
    room.join("agent-earlier")

    async def sleep(_: float) -> None:
        return None

    assert asyncio.run(agents_with_priority(room, "agent-me", attempts=2, sleep=sleep)) == ["agent-earlier"]


def test_an_agent_that_this_one_outranks_never_takes_the_room() -> None:
    """The other half of the tie-break, and the reason a duplicate leaves one agent.

    Both agents run this against the same room at the same moment. Without an
    order they reach the same conclusion and both withdraw, or neither sees the
    other and both stay.
    """
    room = FakeRoom(local_identity="agent-earlier")
    room.join("agent-me")

    async def sleep(_: float) -> None:
        return None

    assert asyncio.run(agents_with_priority(room, "agent-earlier", attempts=2, sleep=sleep)) == []


def test_exactly_one_of_two_simultaneous_agents_stays() -> None:
    """The property the duplicate-dispatch test asserts, decided without coordination."""

    async def sleep(_: float) -> None:
        return None

    def yields(mine: str, theirs: str) -> bool:
        room = FakeRoom(local_identity=mine)
        room.join(theirs)
        return bool(asyncio.run(agents_with_priority(room, mine, attempts=2, sleep=sleep)))

    a, b = "agent-AJ_SfKW4fqFNvWa", "agent-AJ_jqwqtQxaLofR"  # the two from the live run
    assert yields(a, b) != yields(b, a), "one yields and one stays, whichever way round"


def test_a_candidate_is_never_mistaken_for_a_contending_agent() -> None:
    room = FakeRoom(local_identity="agent-me")
    room.join("candidate-42")  # sorts before "agent-me" only if it were an agent

    async def sleep(_: float) -> None:
        return None

    assert asyncio.run(agents_with_priority(room, "agent-me", attempts=2, sleep=sleep)) == []


# --------------------------------------------------------------------------
# The duplicate that arrives after the one-shot check (the live failure)
# --------------------------------------------------------------------------


def test_an_agent_that_outranks_this_one_while_it_waits_takes_the_room() -> None:
    """The half a single check cannot catch.

    A duplicate dispatch lands a few hundred milliseconds behind the first, so
    whether it is visible at one fixed moment is a coin toss. Against real
    LiveKit both agents saw each other and both withdrew on one run, and on the
    next neither saw the other and both stayed — two agents, then none, never
    one. The guard has to hold for as long as we are waiting.
    """
    room = FakeRoom(local_identity="agent-me")

    async def scenario():
        waiting = asyncio.ensure_future(
            wait_for_candidate(room, "candidate-42", timeout=1.0, my_identity="agent-me")
        )
        await asyncio.sleep(0)
        room.join("agent-earlier")  # the duplicate, arriving late
        return await waiting

    with pytest.raises(Outranked, match="agent-earlier"):
        asyncio.run(scenario())


def test_an_agent_this_one_outranks_arriving_late_is_ignored() -> None:
    """The other side of it: the winner keeps waiting for its candidate."""
    room = FakeRoom(local_identity="agent-earlier")

    async def scenario():
        waiting = asyncio.ensure_future(
            wait_for_candidate(room, "candidate-42", timeout=1.0, my_identity="agent-earlier")
        )
        await asyncio.sleep(0)
        room.join("agent-me")  # the duplicate it outranks
        room.join("candidate-42")
        return await waiting

    assert asyncio.run(scenario()).identity == "candidate-42"


def test_an_outranking_agent_already_present_is_yielded_to_before_any_candidate() -> None:
    """Giving up the room beats starting a second session in it."""
    room = FakeRoom(local_identity="agent-me")
    room.join("agent-earlier")
    room.join("candidate-42")

    with pytest.raises(Outranked, match="agent-earlier"):
        asyncio.run(wait_for_candidate(room, "candidate-42", timeout=1.0, my_identity="agent-me"))


def test_without_an_identity_the_wait_is_unguarded() -> None:
    """Callers that are not agents — the assistant worker — are unaffected."""
    room = FakeRoom(local_identity="agent-me")
    room.join("agent-earlier")
    room.join("candidate-42")

    assert asyncio.run(wait_for_candidate(room, "candidate-42", timeout=1.0)).identity == "candidate-42"


@pytest.mark.parametrize(
    ("identity", "mine", "expected"),
    [
        ("agent-a", "agent-b", True),
        ("agent-b", "agent-a", False),
        ("agent-a", "agent-a", False),
        ("candidate-a", "agent-b", False),
        ("agent-a", None, False),
    ],
)
def test_who_outranks_whom(identity: str, mine: str | None, expected: bool) -> None:
    assert outranks(identity, mine) is expected
