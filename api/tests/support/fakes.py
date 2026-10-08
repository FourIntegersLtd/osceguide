"""In-memory doubles for every port in `app/core/ports.py`.

Same style as `osce_assessment.testing.doubles`: each fake records what it
was asked to do, and failure is injected through a constructor argument so a
test can say "the third email fails" without a mock.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from app.core.ports import (
    EmailDeliveryFailed,
    GuidelinePassage,
    Passage,
    SourcePassages,
    SsoBrokerUnavailable,
    SsoIdentity,
    WebAnswer,
)

FIXED_NOW = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, now: datetime = FIXED_NOW) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now = self._now + timedelta(seconds=seconds)

    def set(self, now: datetime) -> None:
        """Move to a moment, rather than by an interval.

        A test about a deadline reads better as "an hour later" than as a sum
        of every step that got there.
        """
        self._now = now


@dataclass(frozen=True)
class SentEmail:
    to: str
    subject: str
    html: str
    reply_to: str | None


@dataclass
class RecordingEmailSender:
    """Records sends, and can be told to fail.

    Two failure shapes, because tests need both: `fail_after` stops working
    once that many have succeeded (a provider that falls over mid-run), and
    `fail_times` refuses the first N attempts (a provider that is briefly down
    and then recovers, which is what a retry policy is for).
    """

    fail_after: int | None = None
    fail_times: int = 0
    sent: list[SentEmail] = field(default_factory=list)
    refused: int = 0

    async def send(self, *, to: str, subject: str, html: str, reply_to: str | None = None) -> str:
        if self.refused < self.fail_times:
            self.refused += 1
            raise EmailDeliveryFailed(f"fake provider refused message to {to}")
        if self.fail_after is not None and len(self.sent) >= self.fail_after:
            raise EmailDeliveryFailed(f"fake provider refused message to {to}")
        self.sent.append(SentEmail(to=to, subject=subject, html=html, reply_to=reply_to))
        return f"fake-msg-{len(self.sent)}"


class FakeEvaluator:
    """An evaluator that records what it was asked to mark.

    Failure is a constructor argument rather than a patched attribute, so a
    test that exercises the failure path reads as a configuration of the fake.
    """

    def __init__(
        self,
        *,
        payload: dict[str, object] | None = None,
        fail_times: int = 0,
    ) -> None:
        self.payload = payload or {"overall": "G", "model_used": "fake-model"}
        self.fail_times = fail_times
        self.calls: list[dict[str, object]] = []

    async def evaluate(
        self,
        *,
        rubric: dict[str, object],
        policy_version: str,
        transcript: list[dict[str, object]],
    ) -> dict[str, object]:
        from app.core.ports import EvaluationFailed

        framework = rubric.get("framework") or {}
        self.calls.append(
            {
                "rubric": rubric,
                # Still recorded under its own name: what a test wants to know
                # is which rubric version an attempt was marked against, and
                # that is the framework's id.
                "framework_id": str(framework.get("id") or "") if isinstance(framework, dict) else "",
                "policy_version": policy_version,
                "turns": len(transcript),
            }
        )
        if self.fail_times > 0:
            self.fail_times -= 1
            raise EvaluationFailed("fake failure")
        return dict(self.payload)


class FakeVoiceTokens:
    """Records what each token was asked to grant."""

    def __init__(self) -> None:
        self.issued: list[dict[str, object]] = []

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
        self.issued.append(
            {
                "identity": identity,
                "room": room,
                "agent_name": agent_name,
                "dispatch_metadata": dispatch_metadata,
                "room_admin": room_admin,
                "can_publish": can_publish,
                "ttl_seconds": ttl_seconds,
            }
        )
        return f"fake-token-{len(self.issued)}"


class FakeVectorIndex:
    """Substring matching standing in for semantic search.

    Enough to prove the slice wires a query to an index and maps ids back to
    rows, which is all this side of the boundary owns.
    """

    def __init__(self) -> None:
        self.documents: dict[str, str] = {}
        self.queries: list[str] = []

    async def index(self, *, doc_id: str, text: str, metadata: dict[str, str]) -> None:
        self.documents[doc_id] = text

    async def search(self, *, query: str, limit: int, kind: str | None = None) -> list[tuple[str, float]]:
        self.queries.append(query)
        hits = [(doc_id, 1.0) for doc_id, text in self.documents.items() if query.lower() in text.lower()]
        return hits[:limit]


@dataclass
class FakeRoomAgents:
    """Records dispatches instead of calling LiveKit.

    Keeps the order of operations, because the order is the invariant: C5 says
    stale agents are removed *before* a dispatch, and a fake that only recorded
    the dispatch could not tell whether that happened.
    """

    calls: list[tuple[str, str]] = field(default_factory=list)
    dispatched: list[dict[str, object]] = field(default_factory=list)
    agents_in_room: int = 0
    fail_dispatch: bool = False
    fail_remove: bool = False
    closed: list[str] = field(default_factory=list)

    async def remove_agents(self, room: str) -> int:
        self.calls.append(("remove", room))
        if self.fail_remove:
            from app.features.voice.errors import VoiceUnavailable

            raise VoiceUnavailable("LiveKit credentials are not configured")
        removed, self.agents_in_room = self.agents_in_room, 0
        return removed

    async def close_room(self, room: str) -> bool:
        self.calls.append(("close", room))
        self.closed.append(room)
        return True

    async def dispatch(self, *, room: str, agent_name: str, metadata: dict[str, str]) -> None:
        self.calls.append(("dispatch", room))
        if self.fail_dispatch:
            from app.features.voice.errors import VoiceUnavailable

            raise VoiceUnavailable("LiveKit is unreachable")
        self.dispatched.append({"room": room, "agent_name": agent_name, "metadata": metadata})


@dataclass
class FakeRoomRecorder:
    """Records what it was asked to record, instead of calling Egress.

    Keeps every start and stop, because the invariant is that a session is
    started once and stopped once: a fake that only kept the last call could
    not tell a double-start from a single one, and a double start is an
    orphaned egress nobody ever stops.
    """

    started: list[tuple[str, str]] = field(default_factory=list)
    stopped: list[str] = field(default_factory=list)
    fail_start: bool = False
    fail_stop: bool = False

    async def start(self, *, room: str, key: str) -> str:
        if self.fail_start:
            from app.features.voice.errors import VoiceUnavailable

            raise VoiceUnavailable("LiveKit is unreachable")
        self.started.append((room, key))
        return f"EG_{len(self.started)}"

    async def stop(self, *, egress_id: str) -> None:
        if self.fail_stop:
            from app.features.voice.errors import VoiceUnavailable

            raise VoiceUnavailable("LiveKit is unreachable")
        self.stopped.append(egress_id)


@dataclass
class FakeTranscriber:
    """Answers canned speech, or refuses, without a model or a recording."""

    text: str = "Hello, what brings you in today? I have had a headache for a week."
    fail: bool = False
    asked: list[str] = field(default_factory=list)

    async def transcribe(self, *, audio_url: str) -> str:
        self.asked.append(audio_url)
        if self.fail:
            from app.core.ports import TranscriptionFailed

            raise TranscriptionFailed("the recording could not be transcribed")
        return self.text


class FakeTranscriptSummariser:
    """Returns a canned payload and records what it was asked to summarise."""

    def __init__(self, *, payload: dict[str, object] | None = None, fail_times: int = 0) -> None:
        self.payload = payload or {
            "summary": "We went over the hip consultation.",
            "agreed_next_steps": ["Offer an examination before the history ends"],
            "topics": ["examination"],
        }
        self.fail_times = fail_times
        self.calls: list[dict[str, object]] = []

    async def summarise(
        self,
        *,
        kind: str,
        transcript: list[dict[str, object]],
        schema: dict[str, object],
        instructions: str,
    ) -> dict[str, object]:
        from app.core.ports import SummaryFailed

        self.calls.append({"kind": kind, "turns": len(transcript), "instructions": instructions})
        if self.fail_times > 0:
            self.fail_times -= 1
            raise SummaryFailed("fake failure")
        return dict(self.payload)


class FakeTutorPromptRenderer:
    """A renderer whose output is unmistakable in an assertion.

    Records the brief it was handed, because what the tutor is told about
    somebody is the thing worth asserting; the wording belongs to the engine
    and has a golden fixture of its own there.
    """

    MARKER = "[fake tutor prompt]"

    def __init__(self) -> None:
        self.briefs: list[dict[str, object]] = []
        self.labels: list[dict[str, str]] = []

    def render(self, *, brief: dict[str, object], labels: Mapping[str, str]) -> str:
        self.briefs.append(dict(brief))
        self.labels.append(dict(labels))
        consultations = brief.get("consultations")
        count = len(consultations) if isinstance(consultations, list) else 0
        return f"{self.MARKER} consultations={count}"


class FakeEmbedder:
    """A deterministic, meaningless vector per text. Enough to prove the wiring."""

    def __init__(self, dimensions: int = 8) -> None:
        self.dimensions = dimensions
        self.calls: list[list[str]] = []

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [[float((hash(t) >> i) % 10) for i in range(self.dimensions)] for t in texts]


class FakeMaterialIndex:
    """Substring matching standing in for retrieval by meaning.

    The slice's own business is deciding *which exams* may be searched and
    turning passages into something the tutor can read out; which passage is
    nearest is the adapter's, and is proved against real pgvector in
    `tests/repository/test_material_index.py`. So this ranks by nothing more
    than whether the words appear, and records what it was asked.
    """

    def __init__(self) -> None:
        self.passages: list[Passage] = []
        self.exam_of: dict[tuple[str, str], str | None] = {}
        self.searches: list[tuple[str, tuple[str, ...], str | None]] = []

    async def upsert(
        self,
        *,
        corpus: str,
        source_id: str,
        exam_id: str | None,
        title: str,
        chunks: Sequence[Mapping[str, Any]],
    ) -> int:
        self.passages = [p for p in self.passages if (p.corpus, p.source_id) != (corpus, source_id)]
        self.exam_of[(corpus, source_id)] = exam_id
        for chunk in chunks:
            self.passages.append(
                Passage(
                    corpus=corpus,
                    source_id=source_id,
                    title=title,
                    text=str(chunk["text"]),
                    section=str(chunk["section"]),
                    score=1.0,
                )
            )
        return len(chunks)

    async def upsert_many(self, sources: Sequence[SourcePassages]) -> int:
        written = 0
        for source in sources:
            written += await self.upsert(
                corpus=source.corpus,
                source_id=source.source_id,
                exam_id=source.exam_id,
                title=source.title,
                chunks=source.chunks,
            )
        return written

    async def indexed_sources(self, *, corpus: str) -> set[str]:
        return {p.source_id for p in self.passages if p.corpus == corpus}

    async def forget(self, *, corpus: str, source_id: str) -> int:
        before = len(self.passages)
        self.passages = [p for p in self.passages if (p.corpus, p.source_id) != (corpus, source_id)]
        self.exam_of.pop((corpus, source_id), None)
        return before - len(self.passages)

    async def search(
        self, *, query: str, exam_ids: Sequence[str], corpus: str | Sequence[str] | None, limit: int
    ) -> list[Passage]:
        self.searches.append((query, tuple(exam_ids), corpus))
        wanted = set(exam_ids)
        corpora = None if corpus is None else {corpus} if isinstance(corpus, str) else set(corpus)
        hits = [
            p
            for p in self.passages
            if query.lower() in p.text.lower()
            and (corpora is None or p.corpus in corpora)
            # The filter the real adapter applies in SQL. Modelled here too,
            # because a fake that returned material the learner does not hold
            # would let an entitlement bug through every test that uses it.
            and (
                self.exam_of.get((p.corpus, p.source_id)) in wanted
                # The help articles every exam shares carry no exam and reach anyone.
                or (p.corpus == "help" and self.exam_of.get((p.corpus, p.source_id)) is None)
            )
        ]
        return hits[:limit]


class FakeGuidelineIndex:
    """Hands back what it was given, and remembers what it was asked."""

    def __init__(self, passages: Sequence[GuidelinePassage] = (), *, delay: float = 0.0) -> None:
        self.passages = list(passages)
        self.delay = delay
        self.searches: list[tuple[str, int, bool]] = []

    async def search(self, *, query: str, limit: int, rerank: bool) -> list[GuidelinePassage]:
        import asyncio

        self.searches.append((query, limit, rerank))
        await asyncio.sleep(self.delay)
        return self.passages[:limit]


class FakeGuidelineWeb:
    """Answers every question with the one answer it was given, and remembers what it was asked."""

    def __init__(self, answer: WebAnswer | None = None) -> None:
        self.reply = answer
        self.questions: list[str] = []

    async def answer(self, *, question: str) -> WebAnswer | None:
        self.questions.append(question)
        return self.reply


class FakeCheckoutSessions:
    """Records what a checkout was asked for, or refuses on demand.

    A fake rather than a patched `httpx`: the port exists so that "this plan
    is not for sale" can be proven without an internet connection or a Stripe
    account, which is the difference between a test that runs and one that
    gets skipped.
    """

    def __init__(self, *, url: str = "https://checkout.stripe.test/c/pay/abc", fails: bool = False) -> None:
        self.url = url
        self.fails = fails
        self.refusal: str | None = None
        self.calls: list[dict[str, str]] = []
        self.prices: list[dict[str, str | int]] = []
        self.refunds: list[dict[str, str | int]] = []

    async def create(
        self,
        *,
        price_id: str,
        customer_email: str,
        success_url: str,
        cancel_url: str,
        client_reference: str,
        referral_code: str | None = None,
        idempotency_key: str | None = None,
    ) -> str:
        from app.core.ports import CheckoutUnavailable

        self.calls.append(
            {
                "idempotency_key": idempotency_key or "",
                "price_id": price_id,
                "customer_email": customer_email,
                "success_url": success_url,
                "cancel_url": cancel_url,
                "referral_code": referral_code or "",
                "client_reference": client_reference,
            }
        )
        if self.fails:
            raise CheckoutUnavailable("stripe is down")
        return self.url

    async def create_price(
        self, *, amount_pence: int, currency: str, product_name: str, plan_code: str
    ) -> str:
        from app.core.ports import CheckoutUnavailable

        if self.fails:
            raise CheckoutUnavailable("stripe is down")
        self.prices.append(
            {
                "amount_pence": amount_pence,
                "currency": currency,
                "product_name": product_name,
                "plan_code": plan_code,
            }
        )
        return f"price_fake_{plan_code}"

    async def refund(self, *, payment_intent_id: str, amount_pence: int, idempotency_key: str) -> None:
        from app.core.ports import CheckoutRefused, CheckoutUnavailable

        if self.refusal:
            raise CheckoutRefused(self.refusal)
        if self.fails:
            raise CheckoutUnavailable("stripe is down")
        self.refunds.append(
            {
                "payment_intent_id": payment_intent_id,
                "amount_pence": amount_pence,
                "idempotency_key": idempotency_key,
            }
        )


@dataclass
class FakeSsoBroker:
    """Stands in for either provider: builds a sign-in URL and vouches for a
    fixed person, whichever the flow asks `for_provider` for.

    `identity` is what `verify` returns; leave it None to make verification
    fail, which is how a test exercises the refused callback without a broker.
    `unavailable` makes both calls raise, for the fail-closed path. Everything
    is recorded so a test can assert what the flow asked of the broker rather
    than only what came back.
    """

    identity: SsoIdentity | None = None
    unavailable: bool = False
    sign_in_urls: list[str] = field(default_factory=list)
    verified: list[str] = field(default_factory=list)
    # SEC-015: the state/nonce the flow put on the sign-in request, and the
    # nonce it expected back, so a test can assert the pair was threaded.
    issued_states: list[str | None] = field(default_factory=list)
    issued_nonces: list[str | None] = field(default_factory=list)
    expected_nonces: list[str | None] = field(default_factory=list)

    def for_provider(self, provider: object) -> FakeSsoBroker:
        """Overriding `get_sso_broker` with a bare fake stands in for
        `SsoBrokers` too — one fake serves whichever provider is configured,
        since a test cares what the flow *did* with the broker, not which
        adapter it would have been in production."""
        del provider
        return self

    def sign_in_url(
        self, *, redirect_url: str, issuer: str | None, state: str | None = None, nonce: str | None = None
    ) -> str:
        if self.unavailable:
            raise SsoBrokerUnavailable("fake broker is down")
        domain = (issuer or "").strip()
        if not domain:
            raise SsoBrokerUnavailable("no issuer configured")
        self.issued_states.append(state)
        self.issued_nonces.append(nonce)
        url = f"https://{domain}/sign-in?redirect_url={redirect_url}"
        self.sign_in_urls.append(url)
        return url

    async def verify(
        self, *, token: str, issuer: str | None = None, expected_nonce: str | None = None
    ) -> SsoIdentity | None:
        del issuer
        if self.unavailable:
            raise SsoBrokerUnavailable("fake broker is down")
        self.expected_nonces.append(expected_nonce)
        self.verified.append(token)
        return self.identity


class FakeEventCounts:
    """Answers an event count from a fixed number, or refuses as unavailable or failed.

    Records what it was asked, so a test can check the filter Mixpanel would get.
    """

    def __init__(self, *, count: int = 0, unavailable: str | None = None, fails: str | None = None) -> None:
        self.count_to_return = count
        self.unavailable = unavailable
        self.fails = fails
        self.calls: list[dict[str, object]] = []

    async def count(self, *, event: str, from_date: date, to_date: date, where: dict[str, str]) -> int:
        """Record the question, then answer or refuse as configured."""
        from app.core.ports import EventCountsFailed, EventCountsUnavailable

        self.calls.append({"event": event, "from_date": from_date, "to_date": to_date, "where": dict(where)})
        if self.unavailable is not None:
            raise EventCountsUnavailable(self.unavailable)
        if self.fails is not None:
            raise EventCountsFailed(self.fails)
        return self.count_to_return
