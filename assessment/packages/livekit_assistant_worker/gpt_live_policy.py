"""Server-enforced GPT-Live session limits, idle handling, shutdown and usage reporting.

Completion is posted to the dispatching backend's ``/api/worker/sessions/{id}/complete``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, fields, is_dataclass
from enum import StrEnum
from typing import Any

from livekit.agents import AgentSession, JobContext, UserInputTranscribedEvent
from livekit.plugins.openai.realtime import GPTLiveSession
from voice_infra import BackendEndpoints
from voice_infra.backend_http import post_json
from voice_infra.worker_config import optional_float

main_logger = logging.getLogger(__name__)

# Default limits for speech-to-speech sessions; see GptLiveSessionPolicyConfig.from_env.
MAX_SECONDS = 300
HARD_WARNING_SECONDS = 60
IDLE_WARNING_SECONDS = 60
IDLE_GRACE_SECONDS = 30

DATA_TYPE_SESSION_WARNING = "gpt_live_session_warning"
DATA_TYPE_SESSION_ENDED = "gpt_live_session_ended"


class SessionEndReason(StrEnum):
    USER_DISCONNECT = "user_disconnect"
    IDLE_TIMEOUT = "idle_timeout"
    HARD_TIMEOUT = "hard_timeout"
    ERROR = "error"


@dataclass(frozen=True)
class GptLiveSessionPolicyConfig:
    max_seconds: float = MAX_SECONDS
    hard_warning_seconds: float = HARD_WARNING_SECONDS
    idle_warning_seconds: float = IDLE_WARNING_SECONDS
    idle_grace_seconds: float = IDLE_GRACE_SECONDS

    @classmethod
    def from_env(cls) -> "GptLiveSessionPolicyConfig":
        """The defaults above, overridden by ``GPT_LIVE_<FIELD>`` where set."""
        return cls(**{f.name: optional_float(f"GPT_LIVE_{f.name.upper()}", getattr(cls, f.name)) for f in fields(cls)})


class GptLiveSessionController:
    """Tracks GPT-Live session time, idle state, and forced shutdown."""

    def __init__(
        self,
        *,
        ctx: JobContext,
        agent: AgentSession,
        session_id: str,
        worker_type: str,
        endpoints: BackendEndpoints | None = None,
        config: GptLiveSessionPolicyConfig | None = None,
    ) -> None:
        self._ctx = ctx
        self._agent = agent
        self._session_id = session_id
        self._worker_type = worker_type
        self._endpoints = endpoints
        self._config = config or GptLiveSessionPolicyConfig.from_env()
        self._started_at = time.monotonic()
        self._last_user_activity = self._started_at
        self._idle_warning_sent = False
        self._hard_warning_sent = False
        self._closing = False
        self._end_reason: SessionEndReason | None = None
        self._tasks: list[asyncio.Task[None]] = []
        self._agent_busy = False

    @property
    def end_reason(self) -> SessionEndReason | None:
        return self._end_reason

    def attach(self) -> None:
        self._tasks.append(asyncio.create_task(self._hard_cap_timer()))
        self._tasks.append(asyncio.create_task(self._idle_monitor()))

        @self._agent.on("user_input_transcribed")
        def _on_user_input(ev: UserInputTranscribedEvent) -> None:
            if ev.is_final:
                self._record_user_activity()

        @self._agent.on("agent_state_changed")
        def _on_agent_state_changed(ev: Any) -> None:
            state = getattr(ev, "new_state", None)
            self._agent_busy = str(state) in {"thinking", "speaking"}
            if self._agent_busy:
                self._last_user_activity = time.monotonic()

        self._ctx.add_shutdown_callback(self._report_usage_on_shutdown)

    def _record_user_activity(self) -> None:
        self._last_user_activity = time.monotonic()
        self._idle_warning_sent = False

    def _elapsed(self) -> float:
        return time.monotonic() - self._started_at

    def _idle_elapsed(self) -> float:
        if self._agent_busy:
            return 0.0
        return time.monotonic() - self._last_user_activity

    async def _hard_cap_timer(self) -> None:
        warning_at = self._config.max_seconds - self._config.hard_warning_seconds
        if warning_at > 0:
            await asyncio.sleep(warning_at)
            if self._closing:
                return
            await self._send_warning(
                reason="time_remaining",
                message=(
                    "You have about one minute left in this voice session. "
                    "Wrap up your question when you can."
                ),
            )
            self._hard_warning_sent = True

        remaining = self._config.max_seconds - self._elapsed()
        if remaining > 0:
            await asyncio.sleep(remaining)

        if self._closing:
            return
        await self.close(SessionEndReason.HARD_TIMEOUT)

    async def _idle_monitor(self) -> None:
        while not self._closing:
            await asyncio.sleep(0.25)
            if self._closing:
                return

            idle_for = self._idle_elapsed()
            if idle_for < self._config.idle_warning_seconds:
                continue

            if not self._idle_warning_sent:
                await self._send_warning(
                    reason="idle_check",
                    message=(
                        "Are you still there? Say something if you need more help, "
                        "or I'll end this session shortly."
                    ),
                )
                self._idle_warning_sent = True
                continue

            if idle_for >= self._config.idle_warning_seconds + self._config.idle_grace_seconds:
                await self.close(SessionEndReason.IDLE_TIMEOUT)
                return

    async def _send_warning(self, *, reason: str, message: str) -> None:
        await self._publish_data(
            {
                "type": DATA_TYPE_SESSION_WARNING,
                "reason": reason,
                "message": message,
                "sessionId": self._session_id,
            }
        )
        await self._speak_commentary(message)

    async def _speak_commentary(self, message: str) -> None:
        try:
            duplex = self._agent.current_agent.duplex_session
            if isinstance(duplex, GPTLiveSession):
                duplex.append_commentary(message)
                return
        except Exception:
            pass
        try:
            handle = self._agent.generate_reply(instructions=message)
            await asyncio.wait_for(handle, timeout=15.0)
        except Exception as exc:
            main_logger.warning("[gpt_live_policy] warning speech failed: %s", exc)

    async def _publish_data(self, payload: dict[str, Any]) -> None:
        try:
            await self._ctx.room.local_participant.publish_data(
                json.dumps(payload).encode("utf-8"),
                reliable=True,
            )
        except Exception as exc:
            main_logger.warning("[gpt_live_policy] publish_data failed: %s", exc)

    async def close(self, reason: SessionEndReason) -> None:
        if self._closing:
            return
        self._closing = True
        self._end_reason = reason

        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

        await self._publish_data(
            {
                "type": DATA_TYPE_SESSION_ENDED,
                "reason": reason.value,
                "sessionId": self._session_id,
            }
        )

        try:
            self._agent.shutdown(drain=True)
        except Exception as exc:
            main_logger.warning("[gpt_live_policy] agent shutdown failed: %s", exc)

        try:
            self._ctx.shutdown(reason=f"gpt_live_{reason.value}")
        except Exception as exc:
            main_logger.warning("[gpt_live_policy] ctx shutdown failed: %s", exc)

    async def _report_usage_on_shutdown(self) -> None:
        usage = getattr(self._agent, "usage", None)
        main_logger.info(
            "[gpt_live_policy] session=%s worker_type=%s end_reason=%s usage=%s",
            self._session_id,
            self._worker_type,
            self._end_reason,
            usage,
        )
        await self._post_session_completion(usage)

    async def _post_session_completion(self, usage: Any) -> None:
        if self._endpoints is None:
            return
        payload = {
            "session_id": self._session_id,
            "worker_type": self._worker_type,
            "end_reason": (self._end_reason or SessionEndReason.USER_DISCONNECT).value,
            "elapsed_seconds": round(self._elapsed(), 3),
            "usage": serialize_usage(usage),
        }
        try:
            status = await post_json(
                self._endpoints.worker_session_complete_url(self._session_id),
                payload,
                headers=self._endpoints.secret_headers(),
                timeout=5.0,
            )
            main_logger.info("[gpt_live_policy] completion POST session=%s status=%s reason=%s", self._session_id, status, payload["end_reason"])
        except Exception as exc:  # noqa: BLE001 — reporting must not fail shutdown
            main_logger.error("[gpt_live_policy] completion POST failed session=%s: %s", self._session_id, exc, exc_info=True)


def serialize_usage(usage: Any) -> dict[str, Any]:
    if usage is None:
        return {}
    value = _jsonable(usage)
    return value if isinstance(value, dict) else {"value": value}


def _jsonable(value: Any) -> Any:
    """JSON-safe copy. LiveKit's AgentSessionUsage is a dataclass holding pydantic
    per-model usage records, which ``dataclasses.asdict`` leaves as objects."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _jsonable(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "__dict__"):
        return {k: _jsonable(v) for k, v in vars(value).items() if not k.startswith("_")}
    return str(value)


def register_gpt_live_session_policy(
    *,
    ctx: JobContext,
    agent: AgentSession,
    session_id: str,
    worker_type: str,
    endpoints: BackendEndpoints | None = None,
    config: GptLiveSessionPolicyConfig | None = None,
) -> GptLiveSessionController:
    controller = GptLiveSessionController(ctx=ctx, agent=agent, session_id=session_id, worker_type=worker_type, endpoints=endpoints, config=config)
    controller.attach()
    return controller
