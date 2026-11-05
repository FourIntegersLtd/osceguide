"""The Resend implementation of the email port.

Imported lazily so the SDK is not needed to run tests or to start the API
without mail configured.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.ports import EmailDeliveryFailed, EmailSender
from app.core.settings import get_settings

# Longer than any healthy Resend call; shorter than a stalled one holding a send slot.
SEND_TIMEOUT_SECONDS = 20


class ResendSender:
    """`EmailSender` backed by the Resend API."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._resend: Any = None
        if self._settings.resend_api_key:
            try:
                import resend  # optional dependency
            except ImportError:  # pragma: no cover - depends on deployment extras
                return
            # Set once here, not per send: sends run in worker threads side by side.
            resend.api_key = self._settings.resend_api_key
            self._resend = resend

    async def send(self, *, to: str, subject: str, html: str, reply_to: str | None = None) -> str:
        """Send one email and return the provider's message id, or raise `EmailDeliveryFailed`."""
        if not self._settings.resend_api_key:
            raise EmailDeliveryFailed("No Resend API key is configured.")
        if self._resend is None:
            raise EmailDeliveryFailed("The Resend SDK is not installed")

        # Built as a named value rather than one literal with a `**` spread in
        # it: the spread hid the required `to` key from the SDK's own
        # TypedDict, which is how a send could go out malformed and typecheck.
        params: dict[str, Any] = {
            "from": self._settings.email_from,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        if reply_to:
            params["reply_to"] = reply_to
        try:
            # The SDK is blocking: on the event loop one slow send would stall every other.
            send_result = await asyncio.wait_for(
                asyncio.to_thread(self._resend.Emails.send, params), SEND_TIMEOUT_SECONDS
            )
        except Exception as exc:  # noqa: BLE001 - any provider error or timeout is a delivery failure
            raise EmailDeliveryFailed(str(exc) or type(exc).__name__) from exc
        return str(send_result.get("id", ""))


def build_email_sender() -> EmailSender:
    return ResendSender()
