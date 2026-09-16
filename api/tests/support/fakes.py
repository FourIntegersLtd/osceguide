"""In-memory doubles for every port in `app/core/ports.py`.

Same style as `osce_assessment.testing.doubles`: each fake records what it
was asked to do, and failure is injected through a constructor argument so a
test can say "the third email fails" without a mock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.core.ports import EmailDeliveryFailed

FIXED_NOW = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, now: datetime = FIXED_NOW) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now = self._now + timedelta(seconds=seconds)


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
        framework_id: str,
        policy_version: str,
        transcript: list[dict[str, object]],
    ) -> dict[str, object]:
        from app.core.ports import EvaluationFailed

        self.calls.append(
            {
                "framework_id": framework_id,
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
        ttl_seconds: int = 3600,
    ) -> str:
        self.issued.append(
            {
                "identity": identity,
                "room": room,
                "agent_name": agent_name,
                "dispatch_metadata": dispatch_metadata,
                "room_admin": room_admin,
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

    async def search(self, *, query: str, limit: int) -> list[tuple[str, float]]:
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

    async def remove_agents(self, room: str) -> int:
        self.calls.append(("remove", room))
        removed, self.agents_in_room = self.agents_in_room, 0
        return removed

    async def dispatch(self, *, room: str, agent_name: str, metadata: dict[str, str]) -> None:
        self.calls.append(("dispatch", room))
        if self.fail_dispatch:
            from app.features.voice.errors import VoiceUnavailable

            raise VoiceUnavailable("LiveKit is unreachable")
        self.dispatched.append({"room": room, "agent_name": agent_name, "metadata": metadata})
