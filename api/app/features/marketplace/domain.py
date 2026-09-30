"""Peers offering each other practice slots.

Someone posts a time they are free; someone else claims it; both join a room at
the appointed hour. The only rule that really matters is that a post is claimed
once — two people press the button at the same moment, and the loser must be
told, not silently double-booked.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

# A session can be joined from twenty minutes before its start time until an hour
# after it, as on the live site. Much earlier leaves someone sitting alone in a
# room wondering whether it is broken.
OPENS_BEFORE_START = timedelta(minutes=20)
CLOSES_AFTER_START = timedelta(hours=1)

CLAIMABLE_STATUSES = frozenset({"available"})
CANCELLABLE_STATUSES = frozenset({"available", "claimed"})
JOINABLE_STATUSES = frozenset({"scheduled", "active"})


# Plain exceptions keep these rules free of HTTP. `service._REFUSALS` turns each
# one into the error a client sees.
class PostUnavailable(Exception):
    pass


class SlotAlreadyClaimed(PostUnavailable):
    """Raised specifically when the slot is gone because somebody else already claimed it.

    A subclass of `PostUnavailable`, not a sibling: `raise_mapped` matches by
    `isinstance` in the order `service._REFUSALS` lists its entries, so this
    must be listed ahead of the plain `PostUnavailable` mapping there or it
    would never be reached. Its own error code exists because "someone beat
    you to it" is worth telling a caller apart from "that slot is gone" —
    the first is nobody's fault and the client can just show the next slot.
    """


class CannotClaimOwnPost(Exception):
    """Raised when the person offering a slot tries to claim it themselves."""


class NotYours(Exception):
    """Raised when someone other than the person who offered a slot tries to withdraw it."""


class SessionNotJoinable(Exception):
    """Raised when a booked session is cancelled, not yet open, or past its join window."""


class TooEarlyToJoin(SessionNotJoinable):
    """Raised specifically when the join window has not opened yet.

    A subclass of `SessionNotJoinable` for the same `raise_mapped` ordering
    reason as `SlotAlreadyClaimed` above. Worth its own code because it is the
    one join refusal that resolves itself — the client can just say "come back
    at ten past" rather than "something is wrong with this session".
    """


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
    status: str


def ensure_claimable(post: PostState, *, claimer_id: str, now: datetime) -> None:
    """Refuse to claim a slot that is gone, already started, or the caller's own."""
    if post.status not in CLAIMABLE_STATUSES:
        if post.status == "claimed":
            raise SlotAlreadyClaimed(f"That slot is no longer available ({post.status}).")
        raise PostUnavailable(f"That slot is no longer available ({post.status}).")
    if post.owner_id == claimer_id:
        raise CannotClaimOwnPost("You cannot claim your own slot.")
    if post.starts_at <= now:
        # Once the start time has passed there is nothing left to join.
        raise PostUnavailable("That slot has already started.")


def ensure_cancellable(post: PostState, *, actor_id: str) -> None:
    """Refuse to withdraw a slot that is not the caller's own or is no longer open."""
    if post.owner_id != actor_id:
        raise NotYours("Only the person who offered a slot can withdraw it.")
    if post.status not in CANCELLABLE_STATUSES:
        raise PostUnavailable(f"A {post.status} slot cannot be withdrawn.")


def may_join(peer_session: SessionState, *, user_id: str) -> bool:
    return user_id in {peer_session.owner_id, peer_session.claimer_id}


def ensure_joinable(peer_session: SessionState, *, now: datetime) -> None:
    """Refuse to join a session that is not scheduled or active, or is outside its join window."""
    if peer_session.status not in JOINABLE_STATUSES:
        raise SessionNotJoinable(f"That session is {peer_session.status} and can no longer be joined.")
    if now < peer_session.starts_at - OPENS_BEFORE_START:
        raise TooEarlyToJoin("That session has not opened yet.")
    if now > peer_session.starts_at + CLOSES_AFTER_START:
        raise SessionNotJoinable("That session has expired.")
