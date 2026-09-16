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
    """Records sends; fails every send once `fail_after` sends have succeeded."""

    fail_after: int | None = None
    sent: list[SentEmail] = field(default_factory=list)

    async def send(self, *, to: str, subject: str, html: str, reply_to: str | None = None) -> str:
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
