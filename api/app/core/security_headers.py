"""Baseline response security headers.

The API answers JSON, not HTML, so it is not itself an XSS surface — but these
headers are cheap defence in depth and several are exactly what an external
auditor greps for. They cost nothing to a JSON client and close a few narrow
holes: a browser tricked into treating a JSON error as HTML (nosniff), the API
origin being framed (DENY), and the referrer leaking a bearer-bearing URL to a
third party (no-referrer). HSTS is emitted only when deployed, since forcing
HTTPS on a plaintext local dev origin would make it unreachable.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

# Static headers applied to every response. A JSON API needs no script or style
# sources, so the CSP is maximally strict: nothing loads, nothing frames it.
_BASE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}

_HSTS = "max-age=63072000; includeSubDomains; preload"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds the baseline headers to every response, and HSTS once deployed."""

    def __init__(self, app: ASGIApp, *, deployed: bool) -> None:
        super().__init__(app)
        self._deployed = deployed

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Run the request, then stamp the headers onto whatever it answered."""
        response = await call_next(request)
        for header_name, header_value in _BASE_HEADERS.items():
            response.headers.setdefault(header_name, header_value)
        if self._deployed:
            response.headers.setdefault("Strict-Transport-Security", _HSTS)
        return response
