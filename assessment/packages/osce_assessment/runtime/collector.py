"""Captures interaction turns in order and streams each one to the sink.

Streaming every message as it arrives is what makes a mid-session crash
recoverable: the sink already holds everything up to the last turn. A failing
``append`` is recorded but never stops the interaction.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from ..contracts import MessageRole, Transcript, TranscriptMessage, TranscriptSink
from ._awaitable import maybe_await

logger = logging.getLogger(__name__)

Clock = Callable[[], datetime]
IdFactory = Callable[[], str]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_message_id() -> str:
    return str(uuid4())


class TranscriptCollector:
    """Builds the transcript as messages arrive and streams each one to the sink."""

    def __init__(
        self,
        attempt_id: str,
        sink: TranscriptSink,
        *,
        clock: Clock = utc_now,
        id_factory: IdFactory = new_message_id,
        runtime_label: str | None = None,
    ) -> None:
        self._attempt_id = attempt_id
        self._sink = sink
        self._clock = clock
        self._id_factory = id_factory
        self._runtime_label = runtime_label
        self._messages: list[TranscriptMessage] = []
        self.append_errors: list[Exception] = []

    @property
    def messages(self) -> tuple[TranscriptMessage, ...]:
        return tuple(self._messages)

    async def on_message(self, role: MessageRole, text: str) -> None:
        """Number and timestamp a new message, keep it, and send it to the sink without failing the session."""
        message = TranscriptMessage(
            role=role,
            message=text,
            timestamp=self._clock(),
            message_id=self._id_factory(),
            seq=len(self._messages),
        )
        self._messages.append(message)
        try:
            await maybe_await(self._sink.append(self._attempt_id, message))
        except Exception as exc:  # noqa: BLE001 — streaming is best-effort
            self.append_errors.append(exc)
            logger.warning(
                "transcript append failed attempt=%s seq=%s: %s",
                self._attempt_id,
                message.seq,
                exc,
            )

    def snapshot(self, *, complete: bool) -> Transcript:
        """The transcript so far, marked complete or not."""
        return Transcript(
            attempt_id=self._attempt_id,
            messages=self.messages,
            complete=complete,
            runtime_label=self._runtime_label,
        )
