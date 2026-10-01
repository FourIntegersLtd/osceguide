"""Ports: the interfaces slices use to reach the outside world.

A slice depends on a Protocol here, never on an SDK. Production wires the real
adapter; tests wire a fake from `tests/support/fakes.py`. That is what lets a
service be tested without patching module attributes.

Every port is `runtime_checkable` so a test can assert a fake conforms. The
ones that speak to a model take and return plain dicts, so `app/core` stays free
of `osce_assessment` and the API starts without it installed.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Annotated, Any, Protocol, runtime_checkable

from fastapi import Depends


@runtime_checkable
class Clock(Protocol):
    """The current time, as a seam a test can freeze."""

    def now(self) -> datetime:
        """The current instant."""
        ...


class SystemClock:
    """The real clock: wall time, in UTC."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class EmailDeliveryFailed(Exception):
    """The provider refused or could not deliver the message."""


@runtime_checkable
class CheckoutSessions(Protocol):
    """Starting a payment with the card processor.

    A port because Stripe is the one outbound dependency this backend *initiates*
    a call to, so a test can prove a plan is refused without reaching Stripe.
    """

    async def create(
        self,
        *,
        price_id: str,
        customer_email: str,
        success_url: str,
        cancel_url: str,
        client_reference: str,
        referral_code: str | None,
    ) -> str:
        """Start a checkout and return the URL to send the customer to.

        `referral_code` rides on the session so the webhook can credit its owner once the
        payment arrives; None for a full-price checkout.

        Raises `CheckoutUnavailable` when the processor cannot be reached or
        refuses; never returns a URL it is not sure of.
        """
        ...

    async def create_price(
        self, *, amount_pence: int, currency: str, product_name: str, plan_code: str
    ) -> str:
        """Create a one-off price with the card processor and return its id.

        On this port rather than one of its own because it is the same processor, key and
        failure: staff pricing a plan and a customer buying one both need Stripe to answer.
        Raises `CheckoutUnavailable` on any failure; never returns an id it is not sure of.
        """
        ...


class CheckoutUnavailable(Exception):
    """The card processor could not start a checkout."""


class EventCountsUnavailable(Exception):
    """Event counts cannot be had at all here: switched off, no secret, or not on
    the analytics plan. Reported as "unconfigured", not as an error."""


class EventCountsFailed(Exception):
    """The analytics provider was asked and did not answer usably."""


@runtime_checkable
class EventCounts(Protocol):
    """Counting raw product-analytics events, to corroborate our own ledger.

    A port because Mixpanel is only ever a second opinion: a test proves the
    reconciliation arithmetic, and what happens when Mixpanel is missing,
    without an account.
    """

    async def count(self, *, event: str, from_date: date, to_date: date, where: dict[str, str]) -> int:
        """How many times `event` fired between two UTC dates, inclusive, whose
        properties equal every entry in `where`.

        Raises `EventCountsUnavailable` when counts cannot be had here at all,
        and `EventCountsFailed` when the provider errs.
        """
        ...


@runtime_checkable
class EmailSender(Protocol):
    """Sending one transactional email, whatever the provider behind it."""

    async def send(self, *, to: str, subject: str, html: str, reply_to: str | None = None) -> str:
        """Send one email and return the provider's message id. Raises EmailDeliveryFailed."""
        ...


def get_clock() -> Clock:
    """Overridden in tests with a FakeClock; never patched."""
    return SystemClock()


ClockDep = Annotated[Clock, Depends(get_clock)]


@runtime_checkable
class VectorIndex(Protocol):
    """Semantic search over whole media items, by id — the media slice's own
    search box. `MaterialIndex` is the other shape: passages out of study
    material, filtered by exam, for the tutor. Both are backed by pgvector (ADR 0019).
    """

    async def index(self, *, doc_id: str, text: str, metadata: dict[str, str]) -> None:
        """Add or replace this document's vector."""
        ...

    async def search(self, *, query: str, limit: int, kind: str | None = None) -> list[tuple[str, float]]:
        """Return `(doc_id, score)` pairs, best first, of one media kind if `kind` is given."""
        ...


@runtime_checkable
class EventBus(Protocol):
    """Fan-out for live updates, so a screen is told rather than asking.

    Transport is Redis pub/sub with more than one API replica, in-process
    otherwise. Nothing durable goes through it: a subscriber that missed an
    event re-reads the read model on reconnect.
    """

    async def publish(self, topic: str, name: str) -> None:
        """Tell every subscriber to `topic` that `name` happened.

        Carries no payload: a subscriber always rebuilds the read model from
        the database.
        """
        ...

    def subscription(self, topics: Sequence[str]) -> AbstractAsyncContextManager[AsyncIterator[str]]:
        """Watch `topics`, yielding the name of each event published to them.

        A context manager, not a bare generator: an async generator runs no
        code until the first `__anext__`, which would leave a window where a
        caller has started watching but an event is published to nobody.
        """
        ...


# --- Models: marking, rendering, summarising, transcribing.


class EvaluationFailed(Exception):
    """The evaluator could not produce a valid result."""


@runtime_checkable
class Evaluator(Protocol):
    """Marks a transcript against a rubric.

    The backend evaluates, always; the worker delivers a transcript and stops,
    never told the evaluation policy. `rubric` is the whole thing — framework,
    marking instructions, clock — frozen onto the attempt when rendered, so a
    re-mark reproduces the original.
    """

    async def evaluate(
        self,
        *,
        rubric: dict[str, object],
        policy_version: str,
        transcript: list[dict[str, object]],
    ) -> dict[str, object]:
        """Return the engine's result payload, already schema-valid.

        Raises `EvaluationFailed` rather than returning a partial result.
        """
        ...


class RenderFailed(Exception):
    """A station could not be rendered into instructions at all."""


@runtime_checkable
class ProfileRenderer(Protocol):
    """Turns a resolved station into the instructions the AI is given.

    The backend renders every prompt; the worker holds no templates and is
    handed finished text. Speaks dicts rather than engine contracts, like
    `Evaluator`, so `app/core` stays free of the engine.
    """

    def render(
        self,
        *,
        station: dict[str, object],
        layout: Sequence[Mapping[str, Any]] | None = None,
        greeting: str | None = None,
        mode: str,
    ) -> dict[str, object]:
        """Return `{"instructions", "greeting", "examiner_context", "debrief_context"}`.

        `layout` is the station template's ordered block list, which says what
        each block of the station is for.

        Raises `RenderFailed` rather than returning empty instructions: the
        worker refuses a job with none, so it should fail here where somebody
        can read the reason, not on connect.
        """
        ...


class TranscriptionFailed(Exception):
    """The audio could not be turned into text."""


@runtime_checkable
class Transcriber(Protocol):
    """Turns recorded audio into words.

    Answers one block of text rather than speaker turns: a room-composite
    recording is a single mixed track, so who said what is recovered
    afterwards by whoever asked, not by this port.
    """

    async def transcribe(self, *, audio_url: str) -> str:
        """Return what was said, or raise `TranscriptionFailed`.

        `audio_url` must be fetchable without credentials of its own — a
        presigned URL, not a bucket path.
        """
        ...


class SummaryFailed(Exception):
    """The model could not produce a summary in the shape asked for."""


@runtime_checkable
class TranscriptSummariser(Protocol):
    """Turns a finished conversation into a small structured record.

    A port for the same reason `Evaluator` is one. `schema` (the JSON schema
    the result must satisfy) and `instructions` (the system prompt) are both
    the caller's, because what a summary should contain is a tutoring
    decision, not an adapter's.
    """

    async def summarise(
        self,
        *,
        kind: str,
        transcript: list[dict[str, object]],
        schema: dict[str, object],
        instructions: str,
    ) -> dict[str, object]:
        """Return a payload valid against `schema`, or raise `SummaryFailed`.

        Raises rather than returning a partial record, since the tutor would
        speak from it as though it were complete.
        """
        ...


@runtime_checkable
class TutorPromptRenderer(Protocol):
    """Renders what is on file about one learner into a tutor's instructions.

    The backend renders every prompt; the worker holds no templates. `labels`
    are this product's words for its own material ("the condition summaries",
    "the slides"), which keeps the engine free of product vocabulary.
    """

    def render(self, *, brief: dict[str, object], labels: Mapping[str, str]) -> str:
        """Return the instructions. Raises `RenderFailed` if it produced none."""
        ...


# --- Retrieval: embedding and finding passages of study material.


@runtime_checkable
class Embedder(Protocol):
    """Turns text into vectors, for searching study material by meaning.

    Declared ahead of its first caller: until the material index lands, the
    tutor's `search_material` tool answers "not configured".
    """

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """One vector per text, in the order given."""
        ...


@dataclass(frozen=True)
class Passage:
    """One retrieved piece of study material, with enough to cite it.

    Carries the text rather than an id to look up, because the tutor speaks
    the answer and citation in the same breath and a second read would put a
    database round trip inside the voice loop.
    """

    corpus: str
    source_id: str
    title: str
    text: str
    section: str
    score: float


@runtime_checkable
class MaterialIndex(Protocol):
    """Semantic search over the study material, filtered by what a learner holds.

    Distinct from `VectorIndex`, which searches whole media items. This one
    retrieves *passages*. The exam filter is a parameter, not something the
    adapter works out, so the entitlement decision stays in the slice —
    testable without an index at all — and a doctor is never read an answer
    out of material they have not bought.
    """

    async def upsert(
        self,
        *,
        corpus: str,
        source_id: str,
        exam_id: str | None,
        title: str,
        chunks: Sequence[Mapping[str, Any]],
    ) -> int:
        """Replace everything held for `(corpus, source_id)` with `chunks`.

        Replace rather than add: re-indexing an edited summary that lost a
        section must lose that section from the index too. Returns how many
        chunks the source now has.
        """
        ...

    async def search(
        self,
        *,
        query: str,
        exam_ids: Sequence[str],
        corpus: str | None,
        limit: int,
    ) -> list[Passage]:
        """Best passages first. An empty `exam_ids` returns nothing.

        Empty means "holds no exam", never "no filter": the caller passes the
        entitled set, and a caller who computed an empty one has just decided
        this person may read nothing.
        """
        ...

    async def indexed_sources(self, *, corpus: str) -> set[str]:
        """Which sources of a corpus the index holds anything for.

        Part of the port, not read from the caller's own storage, so it is
        expressible against a fake. A rule that only ever ran against a real
        adapter once passed its tests with no caller wiring it up at all.
        """
        ...

    async def forget(self, *, corpus: str, source_id: str) -> int:
        """Drop every passage of one source. Returns how many went.

        What unpublishing means here — prevents a withdrawn summary still
        being quoted, with a citation to a page that now 404s.
        """
        ...


# --- Identity: an external SSO broker. The platform owns `users` and issues its
# own tokens (ADR 0004); a broker only answers "who is this, and did they sign in".


class SsoBrokerUnavailable(Exception):
    """The broker is not configured, could not be reached, or refused.

    A plain exception rather than an `AppError`: the calling slice translates
    it into the error it answers with, as `billing` does for
    `CheckoutUnavailable`.
    """


@dataclass(frozen=True)
class SsoIdentity:
    """Who the broker vouched for.

    `subject` is the broker's own stable id for the person, stored against the
    platform user in `user_identities`, so a second sign-in finds the same
    account even if its email has since changed.
    """

    email: str
    name: str
    subject: str


@runtime_checkable
class SsoBroker(Protocol):
    """An external identity provider this platform delegates verification to."""

    def sign_in_url(
        self, *, redirect_url: str, issuer: str | None, state: str | None = None, nonce: str | None = None
    ) -> str:
        """Where to send the browser to start signing in.

        `issuer` is the organisation's stored broker identity — for Clerk, its
        frontend domain. `state` and `nonce` are the SEC-015 anti-forgery
        pair: an OIDC broker (Entra) puts both on the authorization request so
        the provider echoes `state` back and binds `nonce` into the id token;
        a broker whose flow does not carry them (Clerk) ignores both. Raises
        `SsoBrokerUnavailable` rather than returning a URL it is not sure of.
        """
        ...

    async def verify(
        self, *, token: str, issuer: str | None = None, expected_nonce: str | None = None
    ) -> SsoIdentity | None:
        """Check a token the broker handed back, and say who it is for.

        `issuer` is the same value `sign_in_url` reads — ignored by Clerk (one
        secret key serves every partner), but needed by a multi-tenant OIDC
        broker like Entra to know which tenant's signing keys to check against.

        `expected_nonce` (SEC-015) is the nonce the sign-in request carried: an
        OIDC broker refuses an id token that does not echo it, so a captured or
        injected token cannot be replayed. `None` means the flow carries no
        nonce (Clerk).

        Returns None when the token does not verify; raises
        `SsoBrokerUnavailable` when the broker could not be reached. Never
        returns an identity it is not sure of.
        """
        ...


# --- Voice: LiveKit's side of a consultation — joining, staffing and recording the room.


@runtime_checkable
class VoiceTokens(Protocol):
    """Mints the token a browser uses to join a LiveKit room.

    A port so a test can assert what a token was asked to grant without a
    LiveKit project existing.
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
        consultation and cannot be heard in it. Enforced in the token, not by
        hiding a button, because a muted microphone is only a UI state and
        this has to be a guarantee.
        """
        ...


@runtime_checkable
class RoomAgents(Protocol):
    """Putting an agent into a room that already exists, and taking it out.

    Distinct from `VoiceTokens`, which dispatches implicitly via the token's
    room configuration. A supervisor running a circuit has no such moment, so
    the agent must be dispatched explicitly, on demand.
    """

    async def remove_agents(self, room: str) -> int:
        """Remove every agent participant. Returns how many were removed."""
        ...

    async def close_room(self, room: str) -> bool:
        """Close the room for everyone in it once an agent has joined. False if it was not closed."""
        ...

    async def dispatch(self, *, room: str, agent_name: str, metadata: dict[str, str]) -> None:
        """Ask LiveKit to put `agent_name` into `room`.

        Raises `VoiceUnavailable` if LiveKit cannot be reached: a supervisor
        pressing the button needs to know it did not happen.
        """
        ...


@runtime_checkable
class RoomRecorder(Protocol):
    """Recording what is said in a room, to object storage.

    A peer session is two people and no agent, so the recording is the only
    record and what marking is eventually built from. Audio only: the rubric
    is about what was said, and video costs more for nothing that is read.
    """

    async def start(self, *, room: str, key: str) -> str:
        """Begin recording `room` into `key`. Returns the egress id.

        Raises `VoiceUnavailable` if LiveKit or the bucket is not configured,
        so the caller can decide whether that is fatal — for a practice
        session it is not.
        """
        ...

    async def stop(self, *, egress_id: str) -> None:
        """Stop a recording already begun. Stopping a finished one is not an error."""
        ...
