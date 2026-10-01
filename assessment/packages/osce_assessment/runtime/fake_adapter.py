"""A scripted interaction adapter so the engine can run without LiveKit."""

from __future__ import annotations

from collections.abc import Sequence

from ..contracts import AIInteractionProfile, MessageCallback, MessageRole
from ._awaitable import maybe_await

Turn = tuple[MessageRole, str]


class InteractionFailure(RuntimeError):
    """Raised by the fake adapter when scripted to fail part-way."""


class FakeInteractionAdapter:
    """An interaction adapter that plays a fixed script of turns and records how it was called."""

    def __init__(
        self,
        script: Sequence[Turn] = (),
        *,
        fail_after: int | None = None,
    ) -> None:
        self.script = list(script)
        self.fail_after = fail_after
        self.connected = False
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.greetings: list[str] = []
        self.profiles: list[AIInteractionProfile] = []

    async def connect(self) -> None:
        """Mark the adapter connected and count the call."""
        self.connected = True
        self.connect_calls += 1

    async def send_greeting(self, text: str) -> None:
        self.greetings.append(text)

    async def run(self, profile: AIInteractionProfile, on_message: MessageCallback) -> None:
        """Record the profile and replay each scripted turn, failing early when ``fail_after`` says to."""
        self.profiles.append(profile)
        for index, (role, text) in enumerate(self.script):
            if self.fail_after is not None and index == self.fail_after:
                raise InteractionFailure(f"scripted failure before turn {index}")
            await maybe_await(on_message(role, text))

    async def disconnect(self) -> None:
        """Mark the adapter disconnected and count the call."""
        self.connected = False
        self.disconnect_calls += 1
