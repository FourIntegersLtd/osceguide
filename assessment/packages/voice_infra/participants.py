"""Finding the candidate in the room, and noticing a duplicate dispatch.

A room may hold more than one human (an observer, a supervisor, other
candidates waiting their turn), so the candidate is always chosen by the
reference the dispatcher supplied: an exact identity match wins; a substring
match (the client appended a suffix) is accepted only when no exact match is
present. Nothing is ever chosen without a reference.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import Any

Sleep = Callable[[float], Awaitable[None]]

AGENT_IDENTITY_PREFIX = "agent-"

_NO_MATCH, _SUBSTRING, _EXACT = 0, 1, 2


def _match_rank(identity: str, candidate_ref: str) -> int:
    identity = (identity or "").strip()
    candidate_ref = (candidate_ref or "").strip()
    if not identity or not candidate_ref or identity.startswith(AGENT_IDENTITY_PREFIX):
        return _NO_MATCH
    if identity == candidate_ref:
        return _EXACT
    return _SUBSTRING if candidate_ref in identity else _NO_MATCH


def identity_matches(identity: str, candidate_ref: str) -> bool:
    """Exact match, or a substring match when the client appends a suffix. Never an agent, never without a ref."""
    return _match_rank(identity, candidate_ref) > _NO_MATCH


def find_candidate(participants: Iterable[Any], candidate_ref: str) -> Any | None:
    """The participant matching ``candidate_ref``: exact identity first, substring only otherwise."""
    best: Any | None = None
    best_rank = _NO_MATCH
    for participant in participants:
        rank = _match_rank(getattr(participant, "identity", ""), candidate_ref)
        if rank > best_rank:
            best, best_rank = participant, rank
        if best_rank == _EXACT:
            break
    return best


class Outranked(Exception):
    """An agent that outranks this one joined, so this one should give up the room."""


def outranks(identity: str, mine: str | None) -> bool:
    """Whether ``identity`` is an agent this one must yield to.

    Lexicographic on identity, because it is the one piece of information every
    agent in the room already holds and reads the same way. No coordination and
    no shared state: of any set of contenders exactly one finds nothing above
    it.
    """
    return bool(mine) and identity.startswith(AGENT_IDENTITY_PREFIX) and identity < mine


async def wait_for_candidate(
    room: Any, candidate_ref: str, *, timeout: float, my_identity: str | None = None
) -> Any:
    """The participant matching ``candidate_ref``, present now or joining within ``timeout``.

    Given ``my_identity``, the duplicate tie-break runs for the whole wait
    rather than at one fixed moment, and raises `Outranked` if an agent that
    outranks this one turns up.

    Sampling once is not enough, and that was the remaining half of the bug. A
    duplicate dispatch arrives a few hundred milliseconds behind the first, so
    whether the other agent is visible at the moment of a single check is a
    coin toss: in one run both agents saw each other and both withdrew, in the
    next neither saw the other and both stayed. Watching until the candidate
    arrives covers the window duplicates actually land in.
    """
    loop = asyncio.get_running_loop()
    future: asyncio.Future = loop.create_future()

    def consider(participant: Any) -> None:
        if future.done():
            return
        if outranks(participant.identity, my_identity):
            future.set_exception(Outranked(participant.identity))
        elif identity_matches(participant.identity, candidate_ref):
            future.set_result(participant)

    # Registered before the room is read, so nobody can slip through the gap
    # between the two.
    room.on("participant_connected", consider)
    try:
        present = list(room.remote_participants.values())
        # Agents first: giving up the room beats starting a second session in it.
        for participant in present:
            if outranks(participant.identity, my_identity):
                consider(participant)
        if not future.done():
            # `find_candidate` rather than the first identity that matches,
            # because it ranks an exact identity above a lookalike sharing the
            # prefix — `candidate-42` must win over `candidate-421`.
            already = find_candidate(present, candidate_ref)
            if already is not None:
                future.set_result(already)
        return await asyncio.wait_for(future, timeout=timeout)
    finally:
        room.off("participant_connected", consider)


async def agents_with_priority(
    room: Any, my_identity: str, *, attempts: int = 4, delay: float = 1.5, sleep: Sleep = asyncio.sleep
) -> list[str]:
    """Other agents in the room this one must yield to, once they have had time to leave.

    Two different things arrive here. A **stale** agent from a finished job is
    on its way out, and the retry loop is what waits for it. A **simultaneous**
    duplicate dispatch is not on its way out: it is running this same function,
    against the same room, at the same moment — so whatever this agent
    concludes, the other one concludes too.

    That symmetry was the bug. Both agents saw each other and both withdrew,
    leaving the candidate talking to nobody; with slightly different timing
    neither saw the other and both stayed, and the candidate heard two voices.
    A duplicate dispatch produced two agents or none, never one.

    The tie-break is the identity order. It is the one piece of information
    both agents already hold and both read the same way, so it needs no
    coordination and no shared state: an agent yields only to an identity that
    sorts before its own, which means exactly one member of any set of
    contenders finds nothing above it and stays.
    """
    contenders: list[str] = []
    for attempt in range(attempts):
        contenders = sorted(
            p.identity for p in room.remote_participants.values() if outranks(p.identity, my_identity)
        )
        if not contenders or attempt == attempts - 1:
            break
        await sleep(delay)
    return contenders
