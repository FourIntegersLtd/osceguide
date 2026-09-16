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
