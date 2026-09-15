"""Room and agent event wiring for one assistant session.

Each function attaches one concern to the LiveKit emitters and returns; the
session orchestrator decides which apply to the mode it is running.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from osce_assessment.contracts import MessageRole

from .prompts import navigation_mode_prompt
from .transcript import TranscriptRecorder
from .ui_guidance import NavigationModeState

logger = logging.getLogger(__name__)

DATA_TYPE_SCENE_CHANGE = "scene_change"
DATA_TYPE_NAV_MODE_CHOICE = "nav_mode_choice"
SCENE_KEYS = ("phase", "question", "patientLine")
SCENE_STARTED_INPUT = "[New scene started — introduce it now as instructed.]"
REPLY_TIMEOUT_S = 45.0

RenderScene = Callable[[dict[str, Any]], Awaitable[str]]


def wire_transcript_capture(agent: Any, recorder: TranscriptRecorder) -> None:
    @agent.on("user_input_transcribed")
    def _on_user(ev: Any) -> None:
        if getattr(ev, "is_final", False) and str(getattr(ev, "transcript", "")).strip():
            recorder.add(MessageRole.USER, ev.transcript.strip())

    @agent.on("conversation_item_added")
    def _on_item(ev: Any) -> None:
        item = getattr(ev, "item", None)
        text = getattr(item, "text_content", None)
        if getattr(item, "role", None) == "assistant" and text:
            recorder.add(MessageRole.ASSISTANT, str(text).strip())


def wire_delivery_on_end(ctx: Any, deliver: Callable[[], Awaitable[None]]) -> None:
    """Deliver when the client leaves and again on shutdown; delivery itself is idempotent."""
    ctx.add_shutdown_callback(deliver)

    @ctx.room.on("participant_disconnected")
    def _on_participant_disconnected(_participant: Any) -> None:
        asyncio.create_task(deliver())


def wire_navigation_mode_choice(ctx: Any, agent: Any, navigation: NavigationModeState) -> None:
    @ctx.room.on("data_received")
    def _on_choice(data_packet: Any) -> None:
        participant = getattr(data_packet, "participant", None)
        if participant is not None and participant.identity == ctx.room.local_participant.identity:
            return
        msg = json_packet(data_packet)
        if not msg or msg.get("type") != DATA_TYPE_NAV_MODE_CHOICE or not navigation.set(str(msg.get("mode"))):
            return
        asyncio.create_task(_reply(agent, user_input=navigation_mode_prompt(navigation.mode), what="navigation mode"))


def wire_scene_changes(ctx: Any, agent: Any, render_scene: RenderScene) -> None:
    """The browser announces a scene; the backend renders the instructions; the model introduces it."""

    @ctx.room.on("data_received")
    def _on_scene_change(data_packet: Any) -> None:
        msg = json_packet(data_packet)
        if not msg or msg.get("type") != DATA_TYPE_SCENE_CHANGE:
            return
        scene = {key: msg.get(key) for key in SCENE_KEYS if msg.get(key) is not None}
        logger.info("[assistant] scene change phase=%s", scene.get("phase"))
        asyncio.create_task(_announce_scene(agent, render_scene, scene))


async def _announce_scene(agent: Any, render_scene: RenderScene, scene: dict[str, Any]) -> None:
    try:
        instructions = await render_scene(scene)
    except Exception as exc:  # noqa: BLE001 — the session continues on the previous scene
        logger.error("scene change not rendered: %s", exc)
        return
    await _reply(agent, instructions=instructions, user_input=SCENE_STARTED_INPUT, what="scene change")


async def _reply(agent: Any, *, what: str, **kwargs: Any) -> None:
    try:
        await asyncio.wait_for(agent.generate_reply(**kwargs), timeout=REPLY_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001 — a lost reply must not end the session
        logger.warning("%s reply failed: %s", what, exc)


def json_packet(data_packet: Any) -> dict[str, Any] | None:
    raw = getattr(data_packet, "data", data_packet)
    if not isinstance(raw, (bytes, bytearray)):
        return None
    try:
        msg = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return msg if isinstance(msg, dict) else None
