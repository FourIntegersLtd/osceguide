"""Room and agent event wiring for one assistant session.

Each function attaches one concern to the LiveKit emitters and returns; the
session orchestrator decides which apply to the mode it is running.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from osce_assessment.contracts import MessageRole

from .prompts import navigation_mode_prompt
from .transcript import TranscriptRecorder
from .ui_guidance import GuidanceProgress, NavigationModeState
from voice_infra.data_packets import json_packet

logger = logging.getLogger(__name__)

DATA_TYPE_SCENE_CHANGE = "scene_change"
DATA_TYPE_PAUSE = "pause"
DATA_TYPE_RESUME = "resume"
DATA_TYPE_NAV_MODE_CHOICE = "nav_mode_choice"
SCENE_KEYS = ("phase", "question", "patientLine")
SCENE_STARTED_INPUT = "[New scene started — introduce it now as instructed.]"
REPLY_TIMEOUT_S = 45.0
STALL_TIMEOUT_S = 8.0
STALL_INSTRUCTION = (
    "You took too long to answer. In one short sentence say you lost your thread, "
    "then answer what the learner just said if you can, or ask your last question again."
)

RenderScene = Callable[[dict[str, Any]], Awaitable[str]]


def wire_transcript_capture(agent: Any, recorder: TranscriptRecorder) -> None:
    """Record each final user utterance and each assistant message into the transcript."""
    @agent.on("user_input_transcribed")
    def _on_user(ev: Any) -> None:
        """Record a finished spoken turn from the user."""
        if getattr(ev, "is_final", False) and str(getattr(ev, "transcript", "")).strip():
            recorder.add(MessageRole.USER, ev.transcript.strip())

    @agent.on("conversation_item_added")
    def _on_item(ev: Any) -> None:
        """Record a message the assistant has added to the conversation."""
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
    """When the browser sends a navigation mode choice, store it and have the agent acknowledge it."""
    @ctx.room.on("data_received")
    def _on_choice(data_packet: Any) -> None:
        """Handle a data message from the browser, ignoring our own and unrelated ones."""
        participant = getattr(data_packet, "participant", None)
        if participant is not None and participant.identity == ctx.room.local_participant.identity:
            return
        msg = json_packet(data_packet)
        if not msg or msg.get("type") != DATA_TYPE_NAV_MODE_CHOICE or not navigation.set(str(msg.get("mode"))):
            return
        asyncio.create_task(_reply(agent, user_input=navigation_mode_prompt(navigation.mode), what="navigation mode"))


def wire_guidance_progress(agent: Any, progress: GuidanceProgress) -> None:
    """Lower the on-screen progress panel as soon as the agent speaks.

    The panel has to outlive the tool that raised it: the longest wait in a
    guidance turn is the model reading the screenshot, which happens after the
    tool has already returned. Nothing inside the tool can see the end of that,
    but the first word spoken afterwards marks it exactly.
    """

    @agent.on("agent_state_changed")
    def _on_agent_state(ev: Any) -> None:
        """Lower the progress panel when the agent starts speaking."""
        if getattr(ev, "new_state", None) == "speaking":
            asyncio.create_task(progress.done())


def wire_scene_changes(ctx: Any, agent: Any, render_scene: RenderScene) -> None:
    """The browser announces a scene; the backend renders the instructions; the model introduces it.

    A scene change cuts off whatever is being said at once, and only the latest
    scene is ever introduced: a slower render of a scene the learner has already
    left is dropped rather than read after the current one. The rendered script
    replaces the agent's instructions, so the learner's answer is met with the
    scene on screen and not the one the session opened on.

    The browser can also pause the assistant. A scene announced while paused is
    held, not read: the latest one is introduced on resume, so clicking through a
    paused walkthrough does not queue a speech per click.
    """
    announced: dict[str, Any] = {}
    held: dict[str, Any] = {}
    paused = False
    current: asyncio.Task[None] | None = None

    def announce(scene: dict[str, Any]) -> None:
        """Introduce this scene, cancelling the announcement of any scene before it."""
        nonlocal current
        if current is not None and not current.done():
            current.cancel()
        current = asyncio.create_task(_announce_scene(agent, render_scene, scene))

    @ctx.room.on("data_received")
    def _on_scene_change(data_packet: Any) -> None:
        """Start an announcement when the browser reports a scene we have not announced yet."""
        nonlocal paused
        msg = json_packet(data_packet)
        kind = msg.get("type") if msg else None
        if kind == DATA_TYPE_PAUSE:
            paused = True
            asyncio.create_task(_interrupt(agent))
            return
        if kind == DATA_TYPE_RESUME:
            paused = False
            if held:
                announce(dict(held))
                held.clear()
            return
        if not msg or kind != DATA_TYPE_SCENE_CHANGE:
            return
        scene = {key: msg.get(key) for key in SCENE_KEYS if msg.get(key) is not None}
        if scene == announced:
            logger.debug("[assistant] scene change ignored, already announced")
            return
        announced.clear()
        announced.update(scene)
        if paused:
            held.clear()
            held.update(scene)
            return
        logger.info("[assistant] scene change phase=%s", scene.get("phase"))
        announce(scene)


def wire_stall_recovery(agent: Any) -> None:
    """If the agent is still thinking after `STALL_TIMEOUT_S`, cut it off and have it say so and ask again.

    One recovery at a time: state changes during the recovery reply are
    ignored (`recovering`), so a model that cannot answer is re-prompted once
    per stall, not in a loop of recoveries watching recoveries.
    """
    watch: asyncio.Task[None] | None = None
    recovering = False

    async def _recover() -> None:
        """Wait out the allowance, then recover."""
        nonlocal recovering
        await asyncio.sleep(STALL_TIMEOUT_S)
        recovering = True
        logger.warning("[assistant] still thinking after %.0fs; recovering", STALL_TIMEOUT_S)
        try:
            await _interrupt(agent)
            await _reply(agent, instructions=STALL_INSTRUCTION, what="stall recovery")
        finally:
            recovering = False

    @agent.on("agent_state_changed")
    def _on_agent_state(change: Any) -> None:
        """Arm the watch when thinking starts; disarm it on any other state."""
        nonlocal watch
        if recovering:
            return
        thinking = getattr(change, "new_state", None) == "thinking"
        if thinking and (watch is None or watch.done()):
            watch = asyncio.create_task(_recover())
        elif not thinking and watch is not None:
            watch.cancel()
            watch = None


async def _interrupt(agent: Any) -> None:
    """Cut off any speech in progress; nothing playing is not an error."""
    try:
        await agent.interrupt()
    except Exception as exc:  # noqa: BLE001 — nothing playing, or an uninterruptible speech
        logger.debug("no speech to interrupt: %s", exc)


async def _announce_scene(agent: Any, render_scene: RenderScene, scene: dict[str, Any]) -> None:
    """Stop what is playing, render the scene's instructions, make them the agent's and introduce it.

    Cancelled by the next scene change, so a slow render of a scene already left is never read.
    """
    # The opening line or the previous scene may still be playing; stop it now, not after the render.
    await _interrupt(agent)
    try:
        instructions = await render_scene(scene)
    except Exception as exc:  # noqa: BLE001 — the session continues on the previous scene
        logger.error("scene change not rendered: %s", exc)
        return
    try:
        await agent.current_agent.update_instructions(instructions)
    except Exception as exc:  # noqa: BLE001 — the introduction below still carries the scene
        logger.warning("scene instructions not applied: %s", exc)
    await _reply(agent, instructions=instructions, user_input=SCENE_STARTED_INPUT, what="scene change")


async def _reply(agent: Any, *, what: str, **kwargs: Any) -> None:
    """Ask the agent to speak, giving up after a timeout so a lost reply never ends the session."""
    try:
        await asyncio.wait_for(agent.generate_reply(**kwargs), timeout=REPLY_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001 — a lost reply must not end the session
        logger.warning("%s reply failed: %s", what, exc)


