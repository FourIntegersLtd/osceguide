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

# Cloudflare in front of a backend rejects urllib's default "Python-urllib/x.y"
# User-Agent outright (error 1010), so every worker request identifies itself.
USER_AGENT = "osceguide-voice-worker/1"


def request_headers(headers: dict[str, str] | None = None) -> dict[str, str]:
    """The given headers plus our User-Agent, which the caller's values may override."""
    merged = {"User-Agent": USER_AGENT}
    merged.update(headers or {})
    return merged


class WorkerApiAuthError(RuntimeError):
    """Worker route rejected credentials (401/403)."""


@dataclass(frozen=True)
class SyncGetResult:
    """What a blocking JSON request returned: success, status code, parsed object and whether auth was refused."""

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
    """GET a path on the backend with optional query parameters and read a JSON object back."""
    query_string = f"?{urllib.parse.urlencode(query)}" if query else ""
    return sync_get_json_url(
        f"{base_url.rstrip('/')}{path}{query_string}",
        headers=headers,
        timeout=timeout,
        log_prefix=log_prefix,
    )


def sync_get_json_url(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    log_prefix: str = "worker_api",
) -> SyncGetResult:
    """GET a full URL and read a JSON object back; failures come back in the result, not as exceptions."""
    req = urllib.request.Request(url, headers=request_headers(headers), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return SyncGetResult(ok=True, status=resp.status, data=payload if isinstance(payload, dict) else None)
    except urllib.error.HTTPError as exc:
        auth_failed = exc.code in {401, 403}
        (logger.error if auth_failed else logger.warning)("[%s] GET %s HTTP %s", log_prefix, url, exc.code)
        return SyncGetResult(ok=False, status=exc.code, data=None, auth_failed=auth_failed)
    except Exception as exc:  # noqa: BLE001 — reported through the result
        logger.warning("[%s] GET %s failed: %s", log_prefix, url, exc)
        return SyncGetResult(ok=False, status=None, data=None)


async def post_json(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 5.0,
) -> int:
    """POST a JSON body and return only the HTTP status."""
    req_headers = request_headers({"Content-Type": "application/json", **(headers or {})})
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


def sync_post_json(
    base_url: str,
    path: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    log_prefix: str = "worker_api",
) -> SyncGetResult:
    """POST and read a JSON object back; callers keep it off the audio loop with ``asyncio.to_thread``."""
    return sync_post_json_url(
        f"{base_url.rstrip('/')}{path}",
        payload,
        headers=headers,
        timeout=timeout,
        log_prefix=log_prefix,
    )


def sync_post_json_url(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    log_prefix: str = "worker_api",
) -> SyncGetResult:
    """POST to a full URL and read a JSON object back."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers=request_headers({"Content-Type": "application/json", **(headers or {})}), method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            parsed = json.loads(resp.read().decode("utf-8"))
            return SyncGetResult(ok=True, status=resp.status, data=parsed if isinstance(parsed, dict) else None)
    except urllib.error.HTTPError as exc:
        auth_failed = exc.code in {401, 403}
        (logger.error if auth_failed else logger.warning)("[%s] POST %s HTTP %s", log_prefix, url, exc.code)
        return SyncGetResult(ok=False, status=exc.code, data=None, auth_failed=auth_failed)
    except Exception as exc:  # noqa: BLE001 — reported through the result
        logger.warning("[%s] POST %s failed: %s", log_prefix, url, exc)
        return SyncGetResult(ok=False, status=None, data=None)
