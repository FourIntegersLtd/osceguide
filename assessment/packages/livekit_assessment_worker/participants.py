"""Finding the candidate in the room, and noticing a duplicate dispatch."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

Sleep = Callable[[float], Awaitable[None]]

AGENT_IDENTITY_PREFIX = "agent-"


def identity_matches(identity: str, candidate_ref: str) -> bool:
    """Exact match, or a substring match when the client appends a suffix."""
    identity = (identity or "").strip()
    candidate_ref = (candidate_ref or "").strip()
    if not candidate_ref:
        return not identity.startswith(AGENT_IDENTITY_PREFIX)
    return identity == candidate_ref or candidate_ref in identity


async def wait_for_candidate(room: Any, candidate_ref: str, *, timeout: float) -> Any:
    """The participant matching ``candidate_ref``, present now or joining within ``timeout``."""
    for participant in room.remote_participants.values():
        if identity_matches(participant.identity, candidate_ref):
            return participant

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
