"""The Resend implementation of the email port.

Imported lazily so the SDK is not needed to run tests or to start the API
without mail configured.
"""

from __future__ import annotations

from app.core.ports import EmailDeliveryFailed, EmailSender
from app.core.settings import get_settings


class ResendSender:
    """`EmailSender` backed by the Resend API."""

    async def send(self, *, to: str, subject: str, html: str, reply_to: str | None = None) -> str:
        """Send one email and return the provider's message id, or raise `EmailDeliveryFailed`."""
        settings = get_settings()
        if not settings.resend_api_key:
            raise EmailDeliveryFailed("No Resend API key is configured.")

        try:
            import resend  # noqa: PLC0415 - optional dependency
        except ImportError as exc:  # pragma: no cover - depends on deployment extras
            raise EmailDeliveryFailed("The Resend SDK is not installed") from exc

        resend.api_key = settings.resend_api_key
        # Built as a named value rather than one literal with a `**` spread in
        # it: the spread hid the required `to` key from the SDK's own
        # TypedDict, which is how a send could go out malformed and typecheck.
        params: resend.Emails.SendParams = {
            "from": settings.email_from,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        if reply_to:
            params["reply_to"] = reply_to
        try:
            send_result = resend.Emails.send(params)
        except Exception as exc:  # noqa: BLE001 - any provider error is a delivery failure
            raise EmailDeliveryFailed(str(exc)) from exc
        return str(send_result.get("id", ""))


def build_email_sender() -> EmailSender:
    return ResendSender()
