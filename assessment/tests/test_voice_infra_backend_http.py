"""Every worker → backend request carries an explicit User-Agent.

Cloudflare in front of a backend blocks urllib's default agent string
(error 1010) before the request reaches the app, which surfaced as a 403 on
the bootstrap GET while the aiohttp POSTs got through.
"""

from __future__ import annotations

import io
import json
import urllib.request

import pytest

from voice_infra import backend_http


class _Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_request_headers_sets_the_agent_and_keeps_caller_headers() -> None:
    merged = backend_http.request_headers({"X-B2C-Worker-Secret": "s"})
    assert merged["User-Agent"] == backend_http.USER_AGENT
    assert merged["X-B2C-Worker-Secret"] == "s"
    assert not backend_http.USER_AGENT.lower().startswith("python")


def test_request_headers_lets_a_caller_override_the_agent() -> None:
    assert backend_http.request_headers({"User-Agent": "custom"})["User-Agent"] == "custom"


@pytest.mark.parametrize("call", ["get", "post"])
def test_sync_requests_send_the_agent(monkeypatch, call: str) -> None:
    seen: dict[str, str] = {}

    def fake_urlopen(req, timeout):
        seen.update({k.lower(): v for k, v in req.header_items()})
        return _Response(json.dumps({"ok": True}).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    if call == "get":
        result = backend_http.sync_get_json("https://api.example", "/x", headers={"X-Secret": "s"})
    else:
        result = backend_http.sync_post_json("https://api.example", "/x", {"a": 1}, headers={"X-Secret": "s"})

    assert result.ok and result.data == {"ok": True}
    assert seen["user-agent"] == backend_http.USER_AGENT
    assert seen["x-secret"] == "s"


def test_blocking_get_wrapped_in_to_thread_does_not_stall_the_event_loop() -> None:
    """Workers call sync_get_json via asyncio.to_thread; a 2 s backend must not delay other coroutines."""
    import asyncio
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Slow(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            time.sleep(2)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"ok": true}')

        def log_message(self, *_):
            pass

    server = HTTPServer(("127.0.0.1", 0), Slow)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    async def scenario() -> tuple[float, bool]:
        start = time.monotonic()
        call = asyncio.create_task(
            asyncio.to_thread(backend_http.sync_get_json, f"http://127.0.0.1:{server.server_port}", "/x", timeout=10)
        )
        await asyncio.sleep(0.1)
        ticked_after = time.monotonic() - start  # a blocked loop would resume only after ~2 s
        result = await call
        return ticked_after, result.ok

    try:
        ticked_after, ok = asyncio.run(scenario())
    finally:
        server.shutdown()
    assert ok
    assert ticked_after < 0.5
