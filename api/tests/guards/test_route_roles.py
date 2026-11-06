"""Every route admits a stated minimum role, read from the dependency that enforces it.

`app.core.openapi.minimum_role` derives the rung from the route's own
dependencies (`CurrentPrincipal`, `require_org` with its predicate,
`PlatformAdmin`, a stream's principal, the worker secret), and the document
publishes it as `x-capability`. A route none of them guards is either on
`NO_ROLE` below, with a reason, or a failure: the list only shrinks.

That a lower role is really refused is `tests/http/test_route_roles.py`.
"""

from __future__ import annotations

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute

from app.core.openapi import (
    CAPABILITY_KEY,
    PUBLIC,
    admits_platform_admin,
    document_shared_auth_errors,
    minimum_role,
)
from app.core.tenancy import OrgAdmin, OrgReader, PlatformAdmin
from app.main import create_app
from tests.guards._scan import assert_allow_list

SCIM = "the identity provider's SCIM bearer token, checked by the scim service"
# Routes no person's role guards. Each needs a reason; the list only shrinks.
NO_ROLE = {
    "GET /health": "the load balancer's liveness probe, before any auth",
    "POST /api/v1/auth/register": "signing up: nobody has a token yet",
    "POST /api/v1/auth/login": "signing in: the password is the credential",
    "POST /api/v1/auth/refresh": "carries its own refresh token instead",
    "POST /api/v1/auth/exchange-legacy": "carries the legacy token it exchanges",
    "POST /api/v1/auth/password-reset": "a forgotten password has no session",
    "GET /api/v1/auth/invitation/{token}": "emailed invitation token; answers only the sender's name",
    "POST /api/v1/auth/password-reset/confirm": "carries the emailed password reset token",
    "POST /api/v1/auth/email-change/confirm": "carries the emailed confirmation token instead",
    "POST /api/v1/auth/mfa/verify": "carries the MFA challenge token",
    "POST /api/v1/auth/mfa/enrol/start": "carries the MFA challenge token",
    "POST /api/v1/auth/mfa/enrol/confirm": "carries the MFA challenge token",
    "GET /api/v1/auth/sso/sign-in": "starts SSO before any session",
    "POST /api/v1/auth/sso/login": "starts SSO before any session",
    "POST /api/v1/auth/sso/callback": "carries the single-use SSO state",
    "GET /api/v1/sso/saml/{connection_id}/metadata": "the identity provider reads it by URL",
    "POST /api/v1/sso/saml/{connection_id}/acs": "the identity provider posts a signed assertion",
    "GET /api/v1/orgs/{org_slug}/scim/v2/ServiceProviderConfig": SCIM,
    "GET /api/v1/orgs/{org_slug}/scim/v2/Users": SCIM,
    "GET /api/v1/orgs/{org_slug}/scim/v2/Users/{user_id}": SCIM,
    "POST /api/v1/orgs/{org_slug}/scim/v2/Users": SCIM,
    "PUT /api/v1/orgs/{org_slug}/scim/v2/Users/{user_id}": SCIM,
    "PATCH /api/v1/orgs/{org_slug}/scim/v2/Users/{user_id}": SCIM,
    "DELETE /api/v1/orgs/{org_slug}/scim/v2/Users/{user_id}": SCIM,
    "GET /api/v1/orgs/{org_slug}/scim/v2/Groups": SCIM,
    "GET /api/v1/orgs/{org_slug}/scim/v2/Groups/{group_id}": SCIM,
    "POST /api/v1/orgs/{org_slug}/scim/v2/Groups": SCIM,
    "PUT /api/v1/orgs/{org_slug}/scim/v2/Groups/{group_id}": SCIM,
    "PATCH /api/v1/orgs/{org_slug}/scim/v2/Groups/{group_id}": SCIM,
    "DELETE /api/v1/orgs/{org_slug}/scim/v2/Groups/{group_id}": SCIM,
    "GET /api/v1/billing/plans": "the public price list, shown before sign-up",
    "POST /api/v1/billing/webhooks/stripe": "Stripe, verified by its signature",
    "POST /api/v1/growth/arrivals": "records a visitor's partner link before sign-up",
    "GET /api/v1/site/statistics": "the marketing site's public numbers",
    "POST /api/v1/site/messages": "the public contact form (answers a signed-in sender too)",
    "GET /api/v1/media": "published study media is public (drafts only to their admin)",
    "GET /api/v1/media/lookup": "published study media is public",
    "GET /api/v1/media/{slug}": "published study media is public",
}
NO_ROLE_CEILING = 38  # lower only (37 + GET /auth/invitation/{token}, a token route)


def key(route: APIRoute) -> str:
    return f"{sorted(route.methods)[0]} {route.path}"


@pytest.fixture(scope="module")
def routes() -> list[APIRoute]:
    return [r for r in create_app().routes if isinstance(r, APIRoute)]


def test_every_route_has_a_minimum_role_or_a_reason_not_to(routes: list[APIRoute]) -> None:
    unguarded = {key(r) for r in routes if minimum_role(r) is None}
    assert unguarded - NO_ROLE.keys() == set(), "routes no role dependency guards (use one, or list it here)"
    assert_allow_list("NO_ROLE", NO_ROLE, NO_ROLE_CEILING, unguarded)


def test_the_document_publishes_each_routes_minimum_role(routes: list[APIRoute]) -> None:
    document = create_app().openapi()
    wrong = [
        key(r)
        for r in routes
        for method in r.methods
        if document["paths"][r.path][method.lower()].get(CAPABILITY_KEY) != (minimum_role(r) or PUBLIC)
    ]
    assert not wrong, f"x-capability missing or different from the enforced role: {wrong}"


def test_the_guard_reads_the_role_from_the_dependency() -> None:
    """Planted routes: none, a reader, an admin, and a platform route that also reads an org."""
    probe = FastAPI()
    router = APIRouter()

    @router.get("/open")
    async def open_route() -> None:  # pragma: no cover - never called
        return None

    @router.get("/orgs/{org_slug}/read")
    async def read(workspace: OrgReader) -> None:  # pragma: no cover - never called
        return None

    @router.get("/orgs/{org_slug}/admin")
    async def admin(workspace: OrgAdmin) -> None:  # pragma: no cover - never called
        return None

    @router.get("/orgs/{org_slug}/staff-console")
    async def both(workspace: OrgReader, admin: PlatformAdmin) -> None:  # pragma: no cover - never called
        return None

    probe.include_router(router)
    document_shared_auth_errors(probe)
    roles = {r.path: minimum_role(r) for r in probe.routes if isinstance(r, APIRoute)}
    assert roles == {
        "/open": None,
        "/orgs/{org_slug}/read": "org_member",
        "/orgs/{org_slug}/admin": "org_admin",
        "/orgs/{org_slug}/staff-console": "platform_admin",
    }
    admitted = {r.path for r in probe.routes if isinstance(r, APIRoute) and admits_platform_admin(r)}
    assert admitted == {"/orgs/{org_slug}/read", "/orgs/{org_slug}/staff-console"}
    declared = {r.path: sorted(r.responses) for r in probe.routes if isinstance(r, APIRoute)}
    assert declared["/open"] == [] and declared["/orgs/{org_slug}/admin"] == [401, 403]


def test_a_stated_role_may_not_lower_the_enforced_one() -> None:
    probe = FastAPI()
    router = APIRouter()

    @router.get("/orgs/{org_slug}/admin", openapi_extra={CAPABILITY_KEY: "signed_in"})
    async def admin(workspace: OrgAdmin) -> None:  # pragma: no cover - never called
        return None

    probe.include_router(router)
    route = next(r for r in probe.routes if isinstance(r, APIRoute))
    with pytest.raises(RuntimeError, match="below what it enforces"):
        minimum_role(route)
