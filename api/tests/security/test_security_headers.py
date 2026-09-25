"""Response security headers and schema exposure (security regression).

Finding SEC-005 (Low/Medium). The API set no security headers, and it served
`/openapi.json` even when deployed, publishing its whole route inventory to any
unauthenticated caller. These assert the baseline headers ride on an ordinary
response, and that the schema is withdrawn when the app runs deployed.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.db

_EXPECTED = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


async def test_baseline_security_headers_are_present(client: AsyncClient) -> None:
    response = await client.get("/health")
    for name, value in _EXPECTED.items():
        assert response.headers.get(name) == value, f"{name} missing/wrong: {response.headers}"
    assert "Content-Security-Policy" in response.headers


async def test_hsts_is_absent_when_not_deployed(client: AsyncClient) -> None:
    """HSTS on a plaintext local origin would make it unreachable, so it is
    emitted only when deployed."""
    response = await client.get("/health")
    assert "Strict-Transport-Security" not in response.headers


async def test_openapi_schema_is_withheld_when_deployed(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import get_settings
    from app.main import create_app

    monkeypatch.setenv("APP_ENV", "production")
    # A deployed Settings insists on these; supply dummies so we can build the
    # app and inspect the schema route, which is all this test cares about.
    monkeypatch.setenv("RESEND_API_KEY", "test-resend")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    get_settings.cache_clear()
    try:
        deployed_app = create_app()
        transport = ASGITransport(app=deployed_app)
        async with AsyncClient(transport=transport, base_url="http://test") as http:
            schema = await http.get("/openapi.json")
            docs = await http.get("/docs")
        assert schema.status_code == 404, "deployed app must not publish its schema"
        assert docs.status_code == 404, "deployed app must not publish interactive docs"
    finally:
        get_settings.cache_clear()
