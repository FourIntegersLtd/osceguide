"""Best-effort cloud overflow slot release/extend, addressed by endpoints."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .backend_http import post_json
from .config import BackendEndpoints

logger = logging.getLogger(__name__)


async def _post_slot(action: str, room_name: str, endpoints: BackendEndpoints) -> None:
    room = (room_name or "").strip()
    if not room:
        return
    url = endpoints.slot_endpoint(action)
    if not url:
        logger.warning("[cloud_slot] skipping %s: %s not configured for %s", action, endpoints.base_url_env, endpoints.label)
        return
    try:
        status = await post_json(url, endpoints.slot_payload(room), headers=endpoints.secret_headers(), timeout=5.0)
        logger.info("[cloud_slot] %s room=%s backend=%s status=%s", action, room, endpoints.label, status)
    except Exception as exc:  # noqa: BLE001 — best effort
        logger.error("[cloud_slot] %s failed room=%s backend=%s: %s", action, room, endpoints.label, exc)


async def release_cloud_slot_async(room_name: str, endpoints: BackendEndpoints) -> None:
    await _post_slot("release", room_name, endpoints)


async def extend_cloud_slot_async(room_name: str, endpoints: BackendEndpoints) -> None:
    await _post_slot("extend", room_name, endpoints)


def register_cloud_slot_lifecycle(ctx: Any, endpoints: BackendEndpoints) -> None:
    """Extend the slot on start, release it on shutdown."""
    room_name = ctx.room.name

    async def _release() -> None:
        await release_cloud_slot_async(room_name, endpoints)

    ctx.add_shutdown_callback(_release)
    asyncio.create_task(extend_cloud_slot_async(room_name, endpoints))
