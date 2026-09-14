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


async def wait_for_candidate(room: Any, candidate_ref: str, *, timeout: float) -> Any:
    """The participant matching ``candidate_ref``, present now or joining within ``timeout``."""
    present = find_candidate(room.remote_participants.values(), candidate_ref)
    if present is not None:
        return present

    loop = asyncio.get_running_loop()
    future: asyncio.Future = loop.create_future()

    def on_join(participant: Any) -> None:
        if not future.done() and identity_matches(participant.identity, candidate_ref):
            future.set_result(participant)

    room.on("participant_connected", on_join)
    try:
        return await asyncio.wait_for(future, timeout=timeout)
    finally:
        room.off("participant_connected", on_join)


async def other_agents_present(room: Any, my_identity: str, *, attempts: int = 4, delay: float = 1.5, sleep: Sleep = asyncio.sleep) -> list[str]:
    """Identities of other agents still in the room after giving them time to leave."""
    others: list[str] = []
    for attempt in range(attempts):
        others = [
            p.identity
            for p in room.remote_participants.values()
            if p.identity.startswith(AGENT_IDENTITY_PREFIX) and p.identity != my_identity
        ]
        if not others or attempt == attempts - 1:
            break
        await sleep(delay)
    return others
