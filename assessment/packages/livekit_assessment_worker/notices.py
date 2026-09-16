"""Room notices the client publishes mid-interaction, applied to the model's context.

The client owns the clock; when it warns that the interaction is about to end
it publishes ``{"type": "time_warning", "secondsLeft": N}``. The worker adds a
neutral note to the model's context so the persona winds down instead of being
cut off mid-sentence. The note forces no reply, so the model never talks over
the candidate. Only packets from the candidate are honoured.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from voice_infra.data_packets import json_packet, packet_sender_identity
from voice_infra.notices import apply_notice

logger = logging.getLogger(__name__)

DATA_TYPE_TIME_WARNING = "time_warning"
SECONDS_LEFT_KEY = "secondsLeft"


def time_remaining_notice(seconds_left: int) -> str:
    return (
        f"[Notice: this interaction ends in about {seconds_left} seconds. Stay in character. "
        "Keep any remaining replies brief, do not raise new concerns or open new topics, "
        "and if the other person is wrapping up, let them.]"
    )


def seconds_left_from(msg: dict[str, Any]) -> int | None:
    try:
        value = int(msg.get(SECONDS_LEFT_KEY, 0) or 0)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def wire_time_warnings(ctx: Any, session: Any, candidate_identity: str) -> None:
    @ctx.room.on("data_received")
    def _on_data(data_packet: Any) -> None:
        if packet_sender_identity(data_packet) != candidate_identity:
            return
        msg = json_packet(data_packet)
        if not msg or msg.get("type") != DATA_TYPE_TIME_WARNING:
            return
        seconds_left = seconds_left_from(msg)
        if seconds_left is None:
            return
        logger.info("time warning from candidate: %ss left", seconds_left)
        asyncio.create_task(apply_notice(session, time_remaining_notice(seconds_left)))
