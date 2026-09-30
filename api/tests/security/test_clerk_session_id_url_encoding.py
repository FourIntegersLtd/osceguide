"""Clerk session-id URL encoding (security regression).

Finding SEC-019 (Low). `ClerkBroker.verify` reads the `sid` claim from a JWT
whose signature has not yet been checked, then splices it into the outbound
Clerk API path. A crafted `sid` containing `/`, `?` or `#` could reshape the
request the org's Clerk secret key is attached to. This asserts the id is
percent-encoded, so the path segment cannot be broken out of.
"""

from __future__ import annotations

import base64
import json

from app.features.sso import clerk as clerk_mod
from app.features.sso.clerk import ClerkBroker


def _b64(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def _token(payload: dict) -> str:
    return f"{_b64({'alg': 'RS256'})}.{_b64(payload)}.signature"


class _Resp:
    def __init__(self, status: int, data: dict) -> None:
        self.status_code = status
        self._data = data

    def json(self) -> dict:
        return self._data


class _FakeClient:
    def __init__(self, calls: list) -> None:
        self._calls = calls

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    async def post(self, url: str, **_: object) -> _Resp:
        self._calls.append(("POST", url))
        return _Resp(200, {"user_id": "user_abc"})

    async def get(self, url: str, **_: object) -> _Resp:
        self._calls.append(("GET", url))
        return _Resp(
            200,
            {
                "id": "user_abc",
                "email_addresses": [{"id": "e1", "email_address": "candidate@example.com"}],
                "primary_email_address_id": "e1",
                "first_name": "Cand",
                "last_name": "Idate",
            },
        )


async def test_malicious_session_id_is_url_encoded(monkeypatch) -> None:
    calls: list = []
    monkeypatch.setattr(clerk_mod.httpx, "AsyncClient", lambda *a, **k: _FakeClient(calls))

    broker = ClerkBroker(secret_key="sk_test_dummy")
    token = _token({"sid": "sess_1/../../admin", "sub": "user_abc"})

    identity = await broker.verify(token=token, issuer=None)

    post_urls = [url for method, url in calls if method == "POST"]
    assert post_urls, "verify should call Clerk's sessions endpoint"
    url = post_urls[0]
    # The slashes must be encoded so the segment cannot be escaped.
    assert "sess_1%2F..%2F..%2Fadmin" in url
    assert "/sessions/sess_1/../../admin/verify" not in url
    # The happy path still resolves an identity.
    assert identity is not None
    assert identity.email == "candidate@example.com"
