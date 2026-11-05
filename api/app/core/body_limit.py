"""Refuse a request body larger than `max_request_body_bytes` before the app buffers it.

An upload route reads its body into memory (multipart parsing), so with no
ceiling one oversized POST costs a worker its memory and, with several
workers per container, takes the container. The limit is applied to every
route at the edge of the app, so a slice that forgets its own check is still
covered.

Pure ASGI rather than `BaseHTTPMiddleware`: that one wraps the body in a
stream of its own, which would defeat counting it as it arrives.
"""

from __future__ import annotations

import contextlib

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import AppError, ErrorResponse


class RequestTooLarge(AppError):
    """The request body is larger than this API accepts (413)."""

    status = 413
    code = "request_too_large"
    default_message = "That upload is too large. Choose a smaller file."


class _LimitExceeded(Exception):
    """Raised out of `receive` once a body without a declared length passes the limit."""


class BodyLimitMiddleware:
    """Answers 413 for a body over `max_bytes`, by its `Content-Length` or, failing that, as it is read."""

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = dict(scope["headers"]).get(b"content-length", b"").decode("ascii", "replace")
        if declared.isdecimal() and int(declared) > self.max_bytes:
            await self._refuse(scope, send)
            return

        received = 0
        overflowed = False
        passed = False  # the app's own response has begun, too late to swap for a 413
        refused = False

        async def counting_receive() -> Message:
            """Pass the body through, failing once more bytes have arrived than the limit allows."""
            nonlocal received, overflowed
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    overflowed = True
                    raise _LimitExceeded
            return message

        async def tracking_send(message: Message) -> None:
            """Pass the response through; after an overflow, answer 413 in place of whatever the app says.

            FastAPI turns an error raised while it reads a body into its own 400, so the
            exception never reaches this middleware: the response has to be replaced instead.
            """
            nonlocal passed, refused
            if overflowed and not passed:
                if not refused:
                    refused = True
                    await self._refuse(scope, send)
                return
            if message["type"] == "http.response.start":
                passed = True
            await send(message)

        with contextlib.suppress(_LimitExceeded):
            await self.app(scope, counting_receive, tracking_send)
        if overflowed and not passed and not refused:
            await self._refuse(scope, send)

    async def _refuse(self, scope: Scope, send: Send) -> None:
        """Answer 413 in the error-contract shape and close the connection."""
        body = ErrorResponse(
            code=RequestTooLarge.code,
            message=RequestTooLarge.default_message,
            details={"max_bytes": self.max_bytes},
            request_id=scope.get("state", {}).get("request_id"),
        )
        payload = body.model_dump_json().encode()
        await send(
            {
                "type": "http.response.start",
                "status": RequestTooLarge.status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(payload)).encode()),
                    # An unread body on a kept-alive connection would be parsed as the next request.
                    (b"connection", b"close"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": payload})
