"""Stand-ins for the LiveKit objects the worker touches (mirrors the legacy suite's fakes)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Callable


class FakeEmitter:
    def __init__(self) -> None:
        self.handlers: dict[str, list[Callable[..., Any]]] = {}

    def on(self, name: str, fn: Callable[..., Any] | None = None):
        if fn is None:
            def decorator(inner: Callable[..., Any]) -> Callable[..., Any]:
                self.handlers.setdefault(name, []).append(inner)
                return inner
            return decorator
        self.handlers.setdefault(name, []).append(fn)
        return fn

    def off(self, name: str, fn: Callable[..., Any]) -> None:
        self.handlers.get(name, []).remove(fn)

    def emit(self, name: str, *args: Any) -> None:
        for fn in list(self.handlers.get(name, [])):
            fn(*args)


class FakeLocalParticipant:
    """Records what the worker publishes and the RPCs it makes to the browser."""

    def __init__(self, identity: str) -> None:
        self.identity = identity
        self.published: list[dict[str, Any]] = []
        self.rpc_calls: list[dict[str, Any]] = []
        self.rpc_responses: dict[str, Any] = {}

    async def publish_data(self, payload: bytes, **_kwargs: Any) -> None:
        self.published.append(json.loads(payload))

    async def perform_rpc(self, *, destination_identity: str, method: str, payload: str, response_timeout: float) -> str:
        self.rpc_calls.append(
            {"to": destination_identity, "method": method, "payload": json.loads(payload), "timeout": response_timeout}
        )
        response = self.rpc_responses.get(method, {})
        if isinstance(response, Exception):
            raise response
        if callable(response):
            response = response(json.loads(payload))
        return json.dumps(response)

    def messages(self, message_type: str) -> list[dict[str, Any]]:
        return [m for m in self.published if m.get("type") == message_type]


class FakeRoom(FakeEmitter):
    def __init__(self, *, name: str = "room-1", local_identity: str = "agent-local") -> None:
        super().__init__()
        self.name = name
        self.remote_participants: dict[str, Any] = {}
        self.local_participant = FakeLocalParticipant(local_identity)

    def receive(self, message: dict[str, Any], *, identity: str = "user-1") -> None:
        """Deliver a data-channel message as if the browser had published it."""
        self.emit("data_received", SimpleNamespace(data=json.dumps(message).encode(), participant=participant(identity)))

    def join(self, identity: str) -> SimpleNamespace:
        p = participant(identity)
        self.remote_participants[identity] = p
        self.emit("participant_connected", p)
        return p


class FakeJobContext:
    def __init__(self, room: FakeRoom | None = None, *, metadata: str = "{}") -> None:
        self.room = room or FakeRoom()
        self.shutdown_callbacks: list[Callable[..., Any]] = []
        self.job = SimpleNamespace(id="job-1", metadata=metadata)
        self.connect_calls: list[dict[str, Any]] = []
        self.log_context_fields: dict[str, Any] = {}
        self.shutdowns: list[str] = []

    async def connect(self, **kwargs: Any) -> None:
        self.connect_calls.append(kwargs)

    def shutdown(self, *, reason: str = "") -> None:
        self.shutdowns.append(reason)

    def add_shutdown_callback(self, fn: Callable[..., Any]) -> None:
        self.shutdown_callbacks.append(fn)


class FakeAgentSession(FakeEmitter):
    """Records construction kwargs, start(), say() and aclose()."""

    instances: list["FakeAgentSession"] = []

    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        self.kwargs = kwargs
        self.started: dict[str, Any] | None = None
        self.said: list[tuple[str, dict[str, Any]]] = []
        self.closed = False
        FakeAgentSession.instances.append(self)

    async def start(self, **kwargs: Any) -> None:
        self.started = kwargs

    async def say(self, text: str, **kwargs: Any) -> None:
        self.said.append((text, kwargs))

    async def aclose(self) -> None:
        self.closed = True


def participant(identity: str) -> SimpleNamespace:
    return SimpleNamespace(identity=identity)


def user_transcribed(text: str, *, is_final: bool = True) -> SimpleNamespace:
    return SimpleNamespace(transcript=text, is_final=is_final)


def conversation_item(text: str | None, *, role: str = "assistant") -> SimpleNamespace:
    return SimpleNamespace(item=SimpleNamespace(text_content=text, role=role))
