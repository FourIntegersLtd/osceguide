"""The Resend sender sets its key once, sends off the event loop, and gives up on a stalled call."""

from __future__ import annotations

import asyncio
import sys
import threading
import time
import types
from typing import Any

import pytest

from app.core.ports import EmailDeliveryFailed, EmailDeliveryTimedOut
from app.core.settings import get_settings
from app.features.notifications import sender as sender_module


def fake_resend(monkeypatch: pytest.MonkeyPatch, send: Any) -> types.SimpleNamespace:
    module = types.SimpleNamespace(api_key=None, Emails=types.SimpleNamespace(send=send))
    monkeypatch.setitem(sys.modules, "resend", module)
    monkeypatch.setattr(get_settings(), "resend_api_key", "re_test")
    return module


async def test_the_key_is_set_at_construction_and_the_send_runs_in_a_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    threads: list[int] = []

    def send(params: dict[str, Any]) -> dict[str, str]:
        threads.append(threading.get_ident())
        return {"id": "msg-1"}

    module = fake_resend(monkeypatch, send)
    resend_sender = sender_module.ResendSender()
    assert module.api_key == "re_test"

    message_id = await resend_sender.send(to="a@example.com", subject="s", html="<p>x</p>")

    assert message_id == "msg-1"
    assert threads and threads[0] != threading.get_ident()


async def test_a_stalled_provider_call_becomes_a_delivery_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_resend(monkeypatch, lambda params: time.sleep(0.5) or {"id": "late"})
    monkeypatch.setattr(sender_module, "SEND_TIMEOUT_SECONDS", 0.05)
    resend_sender = sender_module.ResendSender()

    with pytest.raises(EmailDeliveryTimedOut):
        await asyncio.wait_for(resend_sender.send(to="a@example.com", subject="s", html="x"), 2)


async def test_a_provider_error_becomes_a_delivery_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def send(params: dict[str, Any]) -> dict[str, str]:
        raise ValueError("bad address")

    fake_resend(monkeypatch, send)
    with pytest.raises(EmailDeliveryFailed, match="bad address"):
        await sender_module.ResendSender().send(to="a@example.com", subject="s", html="x")
