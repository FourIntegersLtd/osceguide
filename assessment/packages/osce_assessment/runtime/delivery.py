"""Idempotent, retried delivery of a completed transcript.

Mirrors the legacy behaviour worth keeping: a fixed retry schedule, and a
guarantee that one attempt's transcript is delivered at most once even when
two teardown paths race to deliver it.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from ..contracts import Transcript, TranscriptSink
from ._awaitable import maybe_await

Sleep = Callable[[float], Awaitable[None]]


@dataclass(frozen=True)
class RetryPolicy:
    """Delay before each attempt; the number of delays is the number of tries."""

    delays: tuple[float, ...] = (0.0, 2.0, 5.0, 10.0)

    @property
    def attempts(self) -> int:
        return len(self.delays)

    @classmethod
    def immediate(cls, attempts: int = 1) -> "RetryPolicy":
        return cls(delays=tuple(0.0 for _ in range(max(1, attempts))))


class DeliveryError(RuntimeError):
    def __init__(self, attempt_id: str, attempts: int, last_error: Exception) -> None:
        super().__init__(
            f"transcript delivery failed for attempt {attempt_id} "
            f"after {attempts} attempt(s): {last_error!r}"
        )
        self.attempt_id = attempt_id
        self.attempts = attempts
        self.last_error = last_error


class TranscriptDelivery:
    def __init__(
        self,
        sink: TranscriptSink,
        *,
        policy: RetryPolicy = RetryPolicy(),
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._sink = sink
        self._policy = policy
        self._sleep = sleep
        self._delivered: set[str] = set()
        self._locks: dict[str, asyncio.Lock] = {}

    def is_delivered(self, attempt_id: str) -> bool:
        return attempt_id in self._delivered

    async def deliver(self, transcript: Transcript) -> bool:
        """Deliver once. Returns True if this call delivered, False if already done."""
        attempt_id = transcript.attempt_id
        lock = self._locks.setdefault(attempt_id, asyncio.Lock())
        async with lock:
            if attempt_id in self._delivered:
                return False
            last_error: Exception | None = None
            for delay in self._policy.delays:
                if delay > 0:
                    await self._sleep(delay)
                try:
                    await maybe_await(self._sink.complete(attempt_id, transcript))
                except Exception as exc:  # noqa: BLE001 — retried below
                    last_error = exc
                    continue
                self._delivered.add(attempt_id)
                return True
            assert last_error is not None
            raise DeliveryError(attempt_id, self._policy.attempts, last_error)
