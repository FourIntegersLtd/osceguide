"""End-of-turn → first-agent-audio latency logging for voice sessions."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from livekit.agents import ConversationItemAddedEvent
from livekit.agents.llm.chat_context import ChatMessage, MetricsReport

if TYPE_CHECKING:
    from livekit.agents import AgentSession

logger = logging.getLogger(__name__)


@dataclass
class UserTurnMetrics:
    end_of_turn_delay_ms: float | None = None
    transcription_delay_ms: float | None = None
    on_user_turn_completed_delay_ms: float | None = None


@dataclass
class ConversationLatencyTracker:
    """Log per-turn latency from ChatMessage.metrics (LiveKit Agents 1.7+)."""

    label: str
    room: str | None = None
    _user_turn_metrics: UserTurnMetrics = field(default_factory=UserTurnMetrics, init=False)

    def attach(self, agent: "AgentSession") -> None:
        @agent.on("conversation_item_added")
        def _on_conversation_item_added(ev: ConversationItemAddedEvent) -> None:
            item = ev.item
            if not isinstance(item, ChatMessage):
                return
            report: MetricsReport = item.metrics
            if item.role == "user":
                self._user_turn_metrics = UserTurnMetrics(
                    end_of_turn_delay_ms=_ms(report.get("end_of_turn_delay")),
                    transcription_delay_ms=_ms(report.get("transcription_delay")),
                    on_user_turn_completed_delay_ms=_ms(report.get("on_user_turn_completed_delay")),
                )
                return
            if item.role != "assistant":
                return
            parts = format_assistant_latency_log_parts(room=self.room, assistant_report=report, user_metrics=self._user_turn_metrics)
            if parts:
                logger.info("[LATENCY:%s] %s", self.label, " | ".join(parts))
            self._user_turn_metrics = UserTurnMetrics()


def format_assistant_latency_log_parts(*, room: str | None, assistant_report: Any, user_metrics: UserTurnMetrics) -> list[str]:
    parts: list[str] = []
    if room:
        parts.append(f"room={room}")
    e2e = _ms(assistant_report.get("e2e_latency"))
    if e2e is not None:
        parts.append(f"e2e_latency={e2e:.0f}ms")
    if user_metrics.transcription_delay_ms is not None:
        parts.append(f"transcription={user_metrics.transcription_delay_ms:.0f}ms")
    if user_metrics.end_of_turn_delay_ms is not None:
        parts.append(f"eou_delay={user_metrics.end_of_turn_delay_ms:.0f}ms")
    if user_metrics.on_user_turn_completed_delay_ms is not None:
        parts.append(f"user_turn_completed={user_metrics.on_user_turn_completed_delay_ms:.0f}ms")
    for key, name in (("llm_node_ttft", "llm_ttft"), ("tts_node_ttfb", "tts_ttfb"), ("playback_latency", "playback_latency")):
        value = _ms(assistant_report.get(key))
        if value is not None:
            parts.append(f"{name}={value:.0f}ms")
    return parts


def _ms(value: float | None) -> float | None:
    return None if value is None else value * 1000
