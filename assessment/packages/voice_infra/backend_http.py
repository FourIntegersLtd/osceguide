"""HTTP helpers for worker → backend calls. Authentication comes from the endpoints."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class WorkerApiAuthError(RuntimeError):
    """Worker route rejected credentials (401/403)."""


@dataclass(frozen=True)
class SyncGetResult:
    ok: bool
    status: int | None
    data: dict[str, Any] | None
    auth_failed: bool = False


def sync_get_json(
    base_url: str,
    path: str,
    *,
    query: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    log_prefix: str = "worker_api",
) -> SyncGetResult:
    qs = f"?{urllib.parse.urlencode(query)}" if query else ""
    url = f"{base_url.rstrip('/')}{path}{qs}"
    req = urllib.request.Request(url, headers=dict(headers or {}), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return SyncGetResult(ok=True, status=resp.status, data=payload if isinstance(payload, dict) else None)
    except urllib.error.HTTPError as exc:
        auth_failed = exc.code in {401, 403}
        (logger.error if auth_failed else logger.warning)("[%s] GET %s HTTP %s", log_prefix, path, exc.code)
        return SyncGetResult(ok=False, status=exc.code, data=None, auth_failed=auth_failed)
    except Exception as exc:  # noqa: BLE001 — reported through the result
        logger.warning("[%s] GET %s failed: %s", log_prefix, path, exc)
        return SyncGetResult(ok=False, status=None, data=None)


async def post_json(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 5.0,
) -> int:
    req_headers = {"Content-Type": "application/json", **(headers or {})}
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            json=payload,
            headers=req_headers,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            # Do not wait for the body: these routes only use the status, and
            # some finish their response body after lengthy processing.
            return resp.status
