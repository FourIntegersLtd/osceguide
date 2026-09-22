"""Ports: the interfaces slices use to reach the outside world.

A slice depends on a Protocol here, never on an SDK. Production wires the real
adapter; tests wire a fake from `tests/support/fakes.py`. That is what lets a
service be tested without patching module attributes.

Every port is `runtime_checkable` so a test can assert a fake conforms.
Protocols are added when the first slice needs them; keep this file small.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from typing import Annotated, Protocol, runtime_checkable

from fastapi import Depends

# Re-exported so every existing caller keeps one import for "a port". The
# model-facing, identity and retrieval halves live next door only because the
# file outgrew its cap.
from app.core.ports_identity import (
    SsoBroker as SsoBroker,
)
from app.core.ports_identity import (
    SsoBrokerUnavailable as SsoBrokerUnavailable,
)
from app.core.ports_identity import (
    SsoIdentity as SsoIdentity,
)
from app.core.ports_models import (
    EvaluationFailed as EvaluationFailed,
)
from app.core.ports_models import (
    Evaluator as Evaluator,
)
from app.core.ports_models import (
    ProfileRenderer as ProfileRenderer,
)
from app.core.ports_models import (
    RenderFailed as RenderFailed,
)
from app.core.ports_models import (
    SummaryFailed as SummaryFailed,
)
from app.core.ports_models import (
    TranscriptSummariser as TranscriptSummariser,
)
from app.core.ports_models import (
    TutorPromptRenderer as TutorPromptRenderer,
)
from app.core.ports_retrieval import (
    Embedder as Embedder,
)
from app.core.ports_retrieval import (
    MaterialIndex as MaterialIndex,
)
from app.core.ports_retrieval import (
    Passage as Passage,
)


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class EmailDeliveryFailed(Exception):
    """The provider refused or could not deliver the message."""


@runtime_checkable
class CheckoutSessions(Protocol):
    """Starting a payment with the card processor.

    A port because Stripe is the one outbound dependency this backend *initiates* a
    call to, and a test that had to reach Stripe to prove a plan is refused
    would not be run. The webhook that finishes the purchase needs no port:
    it arrives as an HTTP request and is verified from its signature.
    """

    async def create(
        self, *, price_id: str, customer_email: str, success_url: str, cancel_url: str, client_reference: str
    ) -> str:
        """Start a checkout and return the URL to send the customer to.

        Raises `CheckoutUnavailable` when the processor cannot be reached or
        refuses. Never returns a URL it is not sure of: sending somebody to a
        broken checkout is worse than telling them it did not work.
        """
        ...


class CheckoutUnavailable(Exception):
    """The card processor could not start a checkout."""


@runtime_checkable
class EmailSender(Protocol):
    async def send(self, *, to: str, subject: str, html: str, reply_to: str | None = None) -> str:
        """Send one email and return the provider's message id. Raises EmailDeliveryFailed."""
        ...


def get_clock() -> Clock:
    """Overridden in tests with a FakeClock; never patched."""
    return SystemClock()


ClockDep = Annotated[Clock, Depends(get_clock)]


@runtime_checkable
class VoiceTokens(Protocol):
    """Mints the token a browser uses to join a LiveKit room.

    A port because the SDK is an implementation detail, and because a test
    should be able to assert what a token was asked to grant without a LiveKit
    project existing.
    """

    def issue(
        self,
        *,
        identity: str,
        room: str,
        agent_name: str | None,
        dispatch_metadata: dict[str, str] | None,
        room_admin: bool = False,
        can_publish: bool = True,
        ttl_seconds: int = 3600,
    ) -> str:
        """Return a signed join token.

        `can_publish=False` is an examiner watching a station: they hear the
        consultation and cannot be heard in it. Enforced in the token rather
        than by hiding a button, because a muted microphone is a UI state and
        this has to be a guarantee — a candidate must not be able to be
        prompted, and the transcript must stay theirs.
        """
        ...


@runtime_checkable
class RoomAgents(Protocol):
    """Putting an agent into a room that already exists, and taking it out.

    Distinct from `VoiceTokens`, which dispatches implicitly: a candidate
    joining their own attempt carries the agent in their token's room
    configuration. A supervisor running a circuit has no such moment — the room
    is already up and the candidates are already in it — so the agent has to be
    dispatched explicitly, into a room, on demand.
    """

    async def remove_agents(self, room: str) -> int:
        """Remove every agent participant. Returns how many were removed."""
        ...

    async def dispatch(self, *, room: str, agent_name: str, metadata: dict[str, str]) -> None:
        """Ask LiveKit to put `agent_name` into `room`.

        Raises `VoiceUnavailable` if LiveKit cannot be reached: a supervisor
        pressing the button needs to know it did not happen.
        """
        ...


@runtime_checkable
class VectorIndex(Protocol):
    """Semantic search over whole media items, by id.

    The media slice's own search box: a query in, a ranked list of items out,
    and the reader is shown the item. `ports_models.MaterialIndex` is the other
    shape — passages out of material, filtered by exam — and the tutor uses
    that one. Two ports rather than one general one because the media search
    wants an item and the tutor wants a paragraph it can quote, and a port that
    served both would be honest about neither.

    pgvector settled the provider question for the tutor's index; whether this
    one adopts the same adapter or stays with b2c's Pinecone is M-3 in
    `docs/OPEN-QUESTIONS.md`.
    """

    async def index(self, *, doc_id: str, text: str, metadata: dict[str, str]) -> None: ...

    async def search(self, *, query: str, limit: int) -> list[tuple[str, float]]:
        """Return `(doc_id, score)` pairs, best first."""
        ...


@runtime_checkable
class EventBus(Protocol):
    """Fan-out for live updates, so a screen is told rather than asking.

    A port because the transport is an implementation detail: Redis pub/sub in
    a deployment with more than one API replica, an in-process bus when there
    is one. Nothing durable goes through it — a subscriber that missed an event
    re-reads the read model when it reconnects, which is also what makes a
    dropped connection harmless.
    """

    async def publish(self, topic: str, name: str) -> None:
        """Tell every subscriber to `topic` that `name` happened.

        Deliberately carries no payload. A subscriber rebuilds the read model
        from the database, so a screen cannot be updated with a shape that was
        assembled by a writer who knew less than the reader does — and nothing
        about anybody's data crosses the bus.
        """
        ...

    def subscription(self, topics: Sequence[str]) -> AbstractAsyncContextManager[AsyncIterator[str]]:
        """Watch `topics`, yielding the name of each event published to them.

        A context manager rather than a bare generator because *when* the
        subscription starts has to be something the caller can be sure of. An
        async generator does not run a line of its body until the first
        `__anext__`, so a caller that starts one and then reads the database
        has a window in which an event is published to nobody — and the screen
        it is feeding stays wrong until something else happens. Entering this
        subscribes; the snapshot is taken inside.
        """
        ...
