"""Peers offering each other practice slots.

Someone posts a time they are free; someone else claims it; both join a room at
the appointed hour. The only rule that really matters is that a post is claimed
once — two people press the button at the same moment, and the loser must be
told, not silently double-booked.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

# How long before the start time a session opens. Joining an hour early leaves
# someone sitting alone in a room wondering whether it is broken.
JOIN_WINDOW = timedelta(minutes=10)

CLAIMABLE_STATUSES = frozenset({"available"})
CANCELLABLE_STATUSES = frozenset({"available", "claimed"})


# Plain exceptions keep these rules free of HTTP. `service._REFUSALS` turns each
# one into the error a client sees.
class PostUnavailable(Exception):
    pass


class CannotClaimOwnPost(Exception):
    pass


class NotYours(Exception):
    pass


@dataclass(frozen=True)
class PostState:
    """The parts of an offered slot that the claim and withdraw rules look at."""

    status: str
    owner_id: str
    starts_at: datetime


@dataclass(frozen=True)
class SessionState:
    """The parts of a booked session that the join rules look at."""

    owner_id: str
    claimer_id: str
    starts_at: datetime


def ensure_claimable(post: PostState, *, claimer_id: str, now: datetime) -> None:
    if post.status not in CLAIMABLE_STATUSES:
        raise PostUnavailable(f"That slot is no longer available ({post.status}).")
    if post.owner_id == claimer_id:
        raise CannotClaimOwnPost("You cannot claim your own slot.")
    if post.starts_at <= now:
        # Once the start time has passed there is nothing left to join.
        raise PostUnavailable("That slot has already started.")


def ensure_cancellable(post: PostState, *, actor_id: str) -> None:
    if post.owner_id != actor_id:
        raise NotYours("Only the person who offered a slot can withdraw it.")
    if post.status not in CANCELLABLE_STATUSES:
        raise PostUnavailable(f"A {post.status} slot cannot be withdrawn.")


def may_join(peer_session: SessionState, *, user_id: str) -> bool:
    return user_id in {peer_session.owner_id, peer_session.claimer_id}


def is_open(peer_session: SessionState, *, now: datetime) -> bool:
    return now >= peer_session.starts_at - JOIN_WINDOW
