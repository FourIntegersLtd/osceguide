"""Ports: the interfaces slices use to reach the outside world.

A slice depends on a Protocol here, never on an SDK. Production wires the real
adapter; tests wire a fake from `tests/support/fakes.py`. That is what lets a
service be tested without patching module attributes.

Every port is `runtime_checkable` so a test can assert a fake conforms.
Protocols are added when the first slice needs them; keep this file small.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from typing import Annotated, Any, Protocol, runtime_checkable

from fastapi import Depends


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class EmailDeliveryFailed(Exception):
    """The provider refused or could not deliver the message."""


@runtime_checkable
class EmailSender(Protocol):
    async def send(self, *, to: str, subject: str, html: str, reply_to: str | None = None) -> str:
        """Send one email and return the provider's message id. Raises EmailDeliveryFailed."""
        ...


def get_clock() -> Clock:
    """Overridden in tests with a FakeClock; never patched."""
    return SystemClock()


ClockDep = Annotated[Clock, Depends(get_clock)]


class EvaluationFailed(Exception):
    """The evaluator could not produce a valid result."""


@runtime_checkable
class Evaluator(Protocol):
    """Marks a transcript against a rubric.

    The backend evaluates, always. The LiveKit worker delivers a transcript and
    stops: it cannot import an evaluator, and it is never told the evaluation
    policy, so marking cannot be influenced by whatever ran the conversation.

    `rubric` is the whole thing — the framework, its marking instructions, its
    clock — frozen onto the attempt when it was rendered. It used to be a
    `framework_id` the adapter looked up against the four frameworks the engine
    shipped, which is why a rubric anyone authored could not be marked with.
    Passing it whole also means a re-mark reproduces the original rather than
    using whatever the rubric says by then.
    """

    async def evaluate(
        self,
        *,
        rubric: dict[str, object],
        policy_version: str,
        transcript: list[dict[str, object]],
    ) -> dict[str, object]:
        """Return the engine's result payload, already schema-valid.

        Raises EvaluationFailed rather than returning a partial result: a
        half-marked attempt shown to a candidate is worse than one not yet marked.
        """
        ...


class RenderFailed(Exception):
    """A station could not be rendered into instructions at all."""


@runtime_checkable
class ProfileRenderer(Protocol):
    """Turns a resolved station into the instructions the AI is given.

    The backend renders every prompt; the worker holds no templates and is
    handed finished text. That is the boundary the whole assessment layer is
    built on — a transport that had to understand a station's shape would need
    changing every time an organisation invented a new one.

    Speaks dicts rather than engine contracts for the same reason `Evaluator`
    does: `app/core` stays free of the engine, so the API starts and the suite
    runs without it installed.
    """

    def render(
        self,
        *,
        station: dict[str, object],
        layout: Sequence[Mapping[str, Any]] | None = None,
        greeting: str | None = None,
        mode: str,
    ) -> dict[str, object]:
        """Return `{"instructions", "greeting", "examiner_context"}`.

        `layout` is the station template's ordered block list, which says what
        each block of the station is for. It replaces the `exam_code` this used
        to take: the renderer branched on that string to pick one of three
        formatters, so a new exam could not have a document shape of its own
        without a change here and in the engine.

        Raises `RenderFailed` rather than returning empty instructions: the
        worker refuses a job with none, and it should fail here where somebody
        can read the reason, not on connect.
        """
        ...


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
        ttl_seconds: int = 3600,
    ) -> str:
        """Return a signed join token."""
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
    """Semantic search over study material.

    A port because the provider is undecided — b2c uses Pinecone, and pgvector
    is a candidate now that everything else is in Postgres. Whichever wins, the
    slice depends on this and the tests use a fake.
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
