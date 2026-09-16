"""The Resend implementation of the email port.

Imported lazily so the SDK is not needed to run tests or to start the API
without mail configured.
"""

from __future__ import annotations

from app.core.ports import EmailDeliveryFailed, EmailSender
from app.core.settings import get_settings


class ResendSender:
    async def send(self, *, to: str, subject: str, html: str, reply_to: str | None = None) -> str:
        settings = get_settings()
        if not settings.resend_api_key:
            raise EmailDeliveryFailed("No Resend API key is configured.")

        try:
            import resend  # noqa: PLC0415 - optional dependency
        except ImportError as exc:  # pragma: no cover - depends on deployment extras
            raise EmailDeliveryFailed("The Resend SDK is not installed") from exc

        resend.api_key = settings.resend_api_key
        try:
            result = resend.Emails.send(
                {
                    "from": settings.email_from,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                    **({"reply_to": reply_to} if reply_to else {}),
                }
            )
        except Exception as exc:  # noqa: BLE001 - any provider error is a delivery failure
            raise EmailDeliveryFailed(str(exc)) from exc
        return str(result.get("id", ""))


def build_email_sender() -> EmailSender:
    return ResendSender()
