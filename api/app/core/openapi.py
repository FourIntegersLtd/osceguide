"""OpenAPI is the frontend's contract.

Operation ids are derived from the route's tag and function name so the
generated TypeScript client has stable, readable names (`health_get_health`),
and every slice registers a tag here so the document groups by domain.

The document also carries the error vocabulary: `x-codes` on each response
says what that operation can return, and `ErrorResponse.code` is an enum of
every code in the app, so a client switches on values the compiler knows.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from fastapi import FastAPI
from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.core.errors import error_codes

# Raised by `require_org`, so it applies to every org-scoped route rather than
# to any one slice's service.
ORG_SUSPENDED = "organization_suspended"

TAGS: list[dict[str, str]] = [
    {"name": "health", "description": "Liveness and dependency checks"},
    {"name": "identity", "description": "Accounts, sessions and passwords"},
    {"name": "tenancy", "description": "Organisations, membership and access"},
    {"name": "sso", "description": "Which organisation a visitor signs in through"},
    {"name": "inbox", "description": "In-app messages to a person, and announcements to everybody"},
    {"name": "public-site", "description": "What the marketing site reads, and what visitors send us"},
    {"name": "catalog", "description": "Exams and the programmes that offer them"},
    {"name": "rubrics", "description": "What a candidate is marked against, and who wrote it"},
    {"name": "stations", "description": "Scenarios and the templates behind them"},
    {
        "name": "station-generation-profiles",
        "description": "Exported station templates and block hints for autogeneration",
    },
    {"name": "station-sets", "description": "A learner's own practice sets"},
    {"name": "attempts", "description": "One candidate running one scenario"},
    {"name": "voice", "description": "Joining a station with a LiveKit worker"},
    {"name": "entitlements", "description": "Who may attempt what, and why"},
    {"name": "billing", "description": "Plans, payment and what it grants"},
    {"name": "sittings", "description": "Scheduled examinations and training"},
    {"name": "roster", "description": "Trainees, cohorts and groups"},
    {"name": "scim", "description": "SCIM 2.0 provisioning of a roster by an identity provider"},
    {"name": "reviews", "description": "Human judgement about a slot"},
    {"name": "results", "description": "Candidate outcomes and their release"},
    {"name": "dashboard", "description": "What a learner sees on opening the app"},
    {"name": "community", "description": "Questions, replies and comments"},
    {"name": "cv", "description": "A learner's uploaded CV, read into sections"},
    {"name": "marketplace", "description": "Peer practice slots offered and claimed"},
    {"name": "peer-practice", "description": "Being matched with somebody to practise"},
    {"name": "growth", "description": "Partner attribution and referrals"},
    {"name": "media", "description": "Slides, summaries, blogs and podcasts"},
    {"name": "generation", "description": "Drafting content with a model, for the people who author it"},
    {"name": "media-production", "description": "TTS and slide video production for study material"},
    {"name": "assistant", "description": "Help, onboarding and demonstration sessions"},
    {"name": "tutor-memory", "description": "What the tutor remembers about a learner"},
    {"name": "worker", "description": "Routes the LiveKit workers call"},
]


def operation_id(route: APIRoute) -> str:
    """`<tag>_<function name>`, which must be unique across the whole document.

    The generated TypeScript client names a method per operation id, so a
    collision silently loses one of them. `tests/guards/test_routes.py` fails on
    duplicates rather than leaving that to be noticed in the frontend.
    """
    raw = route.tags[0] if route.tags else "api"
    # Starlette types a tag as `str | Enum`; every tag here is a plain string,
    # and an Enum member's value is what appears in the document either way.
    tag = raw if isinstance(raw, str) else str(raw.value)
    # Hyphens are fine in a tag and awkward in a generated method name, so
    # `peer-practice` becomes `peer_practice_join_queue`.
    return f"{tag.replace('-', '_')}_{route.name}"


# The minimum role a route admits, lowest first. Each is one dependency:
# `CurrentPrincipal` (or a stream's principal), then `require_org` with one of
# tenancy's four predicates, then `PlatformAdmin`. A route on two takes the
# higher. Published per operation as `x-capability` so the web can check that a
# screen gates the button that calls it (`web/scripts/check-route-gates.mjs`).
ROLE_LADDER = (
    "signed_in",
    "org_member",
    "org_staff",
    "lead_reviewer",
    "org_admin",
    "institution_admin",
    "platform_admin",
)
CAPABILITY_KEY = "x-capability"
# On an org rung: whether a platform admin who is not a member also passes. `require_org`
# lets one in by default (support reads, running a circuit), never as `OrgAdmin`.
PLATFORM_ADMIN_KEY = "x-platform-admin"
# A per-resource grant, and the rung it narrows. Off the ladder because it is held per partner,
# not per organisation, and refused with the grant's own 403 code. Its dependency is marked with
# `@grant(name)`, so the route's role is derived like any other.
GRANTS = {"partner_reporter": "signed_in"}
_GRANT_DEPENDENCIES: dict[object, str] = {}
Dependency = TypeVar("Dependency", bound=Callable[..., Any])
# Not on the ladder: no person's token reaches these.
PUBLIC = "public"
WORKER = "worker"

# `require_org`'s predicate is `role_policy.policy(name)`; the name says which rung it is.
_POLICY_ROLES = {
    "may_read_org": "org_member",
    "may_run_circuit": "org_staff",
    "may_lead_review": "lead_reviewer",
    "is_org_admin": "org_admin",
    "is_institution_admin": "institution_admin",
}


def grant(name: str) -> Callable[[Dependency], Dependency]:
    """Mark a feature's dependency as enforcing the grant `name` (a `GRANTS` key)."""
    if name not in GRANTS:
        raise RuntimeError(f"unknown grant {name!r}; add it to GRANTS")

    def mark(dependency: Dependency) -> Dependency:
        """Record the dependency so the routes using it are documented as needing the grant."""
        _GRANT_DEPENDENCIES[dependency] = name
        return dependency

    return mark


def _dependency_calls(route: APIRoute) -> list[Any]:
    """Every callable in the route's resolved dependency graph, nested ones included.

    Read from the graph, not from the endpoint's annotations: `from __future__
    import annotations` makes those strings.
    """
    seen = []
    stack = list(route.dependant.dependencies)
    while stack:
        dep = stack.pop()
        if dep.call is not None:
            seen.append(dep.call)
        stack.extend(dep.dependencies)
    return seen


def _is_require_org(call: Any) -> bool:
    """Whether this dependency is one `require_org(...)` built."""
    from app.core.tenancy import OrgGate  # avoids an import cycle

    return isinstance(call, OrgGate)


def _org_rung(gate: Any) -> str:
    """The rung a `require_org(...)` dependency stands for, read from its policy's name.

    Raises rather than guessing: a policy this does not know is a route whose
    role nobody can state, and the route guard should say so.
    """
    name = gate.predicate.name
    if name not in _POLICY_ROLES:
        raise RuntimeError(f"require_org with an unknown policy {name!r}; add it to _POLICY_ROLES")
    return _POLICY_ROLES[name]


def _derived_role(route: APIRoute) -> str | None:
    """The minimum role the route's own dependencies enforce, or None when none do."""
    from app.core.auth import get_principal, require_worker_secret  # avoids an import cycle
    from app.core.streams import get_stream_principal
    from app.core.tenancy import require_platform_admin

    rungs: list[str] = []
    for call in _dependency_calls(route):
        if call is require_worker_secret:
            return WORKER
        if call in _GRANT_DEPENDENCIES:
            return _GRANT_DEPENDENCIES[call]
        if call is require_platform_admin:
            rungs.append("platform_admin")
        elif _is_require_org(call):
            rungs.append(_org_rung(call))
        elif call is get_principal or call is get_stream_principal:
            rungs.append("signed_in")
    return max(rungs, key=ROLE_LADDER.index) if rungs else None


def minimum_role(route: APIRoute) -> str | None:
    """The lowest role this route admits: a `ROLE_LADDER` rung, a grant, `WORKER`, or None.

    A stream cannot take `require_org` (it would hold the request's transaction
    open for the life of the connection) and checks the role in its handler, so
    it states the rung in `openapi_extra={"x-capability": ...}`. A statement may
    only raise what the dependencies enforce, never lower it, and
    `tests/http/test_route_roles.py` calls it to prove it true.
    """
    derived = _derived_role(route)
    stated = (route.openapi_extra or {}).get(CAPABILITY_KEY)
    if stated is None or stated == (derived or PUBLIC):
        return derived
    if stated not in ROLE_LADDER or derived not in ROLE_LADDER:
        raise RuntimeError(f"{route.path}: x-capability {stated!r} cannot stand in for {derived!r}")
    if ROLE_LADDER.index(stated) < ROLE_LADDER.index(derived):
        raise RuntimeError(f"{route.path}: x-capability {stated!r} is below what it enforces, {derived!r}")
    return str(stated)


def admits_platform_admin(route: APIRoute) -> bool:
    """Whether a platform admin outside the organisation passes this route's role check.

    True on `platform_admin`; on an org rung, when every `require_org` it uses allows it
    (a stream that resolves its own workspace uses `resolve_workspace`'s default, which does).
    """
    role = minimum_role(route)
    if role == "platform_admin":
        return True
    if role not in ROLE_LADDER[1:]:
        return False
    return all(call.allow_platform_admin for call in _dependency_calls(route) if _is_require_org(call))


def _authenticates(route: APIRoute) -> bool:
    """Whether a missing, bad or dead credential is refused with 401 on this route."""
    from app.core.auth import get_principal, get_principal_if_present, require_worker_secret
    from app.core.streams import get_stream_principal

    gates = {get_principal, get_principal_if_present, get_stream_principal, require_worker_secret}
    return any(call in gates for call in _dependency_calls(route))


def _declare(route: APIRoute, error: type[Any], *extra_codes: str) -> None:
    """Add one error's code (and any it implies) to the route's `responses`, once."""
    from app.core.errors import ErrorResponse  # avoids an import cycle

    entry = route.responses.setdefault(error.status, {"model": ErrorResponse, "description": ""})
    codes = entry.setdefault("x-codes", [])
    for code in (error.code, *extra_codes):
        if code not in codes:
            codes.append(code)
    entry["description"] = ", ".join(codes)


def document_shared_auth_errors(app: FastAPI) -> None:
    """Declare what the shared auth dependencies raise, and each route's minimum role.

    `unauthenticated`, `forbidden` and `organization_suspended` come from
    `get_principal`, the role dependencies and `require_org`, not from any
    slice's service, so a route's own `error_responses(...)` cannot be trusted
    to list them (org routers once answered 401 and declared only 403).
    Derived from the dependency each route actually uses, so a new route is
    covered the day it is written.

    Written onto `route.responses` and `route.openapi_extra`, not the finished
    document, so the document, `tests/support/declared_codes.py` and the route
    guards all read the same thing.
    """
    from app.core.errors import ACCOUNT_DEACTIVATED_CODE, Forbidden, Unauthenticated  # avoids an import cycle

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        role = minimum_role(route)
        route.openapi_extra = {**(route.openapi_extra or {}), CAPABILITY_KEY: role or PUBLIC}
        if role in ROLE_LADDER[1:-1]:
            route.openapi_extra[PLATFORM_ADMIN_KEY] = admits_platform_admin(route)
        if _authenticates(route):
            _declare(route, Unauthenticated, ACCOUNT_DEACTIVATED_CODE)
        if role in ROLE_LADDER and role != "signed_in":
            _declare(route, Forbidden)
        # A stream on an org rung resolves its own workspace (`resolve_workspace`), which refuses a
        # suspended organisation like `require_org` does.
        org_stream = role in ROLE_LADDER[1:-1] and "{org_slug}" in route.path
        if org_stream or any(_is_require_org(call) for call in _dependency_calls(route)):
            _declare(route, Forbidden, ORG_SUSPENDED)


def install_error_catalogue(app: FastAPI) -> None:
    """Publish the error-code enum into `ErrorResponse` as the document is built.

    Wraps `app.openapi` rather than annotating the model, because the codes
    live on `AppError` subclasses across every slice, not yet imported when
    `core.errors` defines the model — but loaded by the time a document is
    asked for.
    """
    build = app.openapi

    def openapi() -> dict[str, Any]:
        """Build the document as FastAPI would, then patch in the error-code enum."""
        spec = build()
        schema = spec.get("components", {}).get("schemas", {}).get("ErrorResponse")
        if schema is not None:
            schema["properties"]["code"]["enum"] = error_codes()
        return spec

    app.openapi = openapi  # type: ignore[method-assign]


SSE_MEDIA_TYPE = "text/event-stream"
# A route that hands back a document rather than an object: a receipt to
# print or keep. Declared so the generated client knows not to parse it,
# and so the route guard's exemption is stated rather than inferred.
DOCUMENT_MEDIA_TYPE = "text/html"
# A file the browser saves rather than a JSON object: a receipt, a spreadsheet,
# a PDF, a SAML metadata document. A route guard treats these as declared, so
# they do not need a response model that would describe nothing.
SAML_METADATA_MEDIA_TYPE = "application/samlmetadata+xml"
FILE_MEDIA_TYPES = frozenset({DOCUMENT_MEDIA_TYPE, "text/csv", "application/pdf", SAML_METADATA_MEDIA_TYPE})


def sse_responses(frame: type[Any], *errors: type[Any]) -> dict[int | str, dict[str, Any]]:
    """Document a server-sent event stream, including what each frame carries.

    A streaming route has no `response_model` — the body is an unbounded
    sequence of frames, not one object — so without this the generated client
    types it as nothing at all. Naming the frame's schema here keeps the
    contract: a `snapshot` frame's `data` is exactly the model the equivalent
    `GET` returns.

    The `$ref` resolves because every streamed model is also that `GET`'s
    response model; a stream with no polling equivalent should probably not
    exist.
    """
    from app.core.errors import error_responses  # avoids an import cycle

    responses = error_responses(*errors)
    responses[200] = {
        "description": (
            f"An SSE stream: `connected`, then a `snapshot` frame whose `data` is a "
            f"`{frame.__name__}` each time the state changes, and `ping` every 25 seconds."
        ),
        "content": {SSE_MEDIA_TYPE: {"schema": {"$ref": f"#/components/schemas/{frame.__name__}"}}},
    }
    return responses


class MeEventEnvelope(BaseModel):
    """One frame of the `/me/events` fan-in stream: a named event and its small id payload.

    Every other stream's frame is the same shape as its `GET`'s response model, named by
    `sse_responses`. `/me/events` multiplexes many differently-shaped events onto one connection, so
    there is no single response model to point at. This envelope documents the shape every frame
    shares instead: the event's name, and a small object of the ids naming what changed — never the
    changed data itself, which the client re-fetches.

    The events: `attempt`, `practice.session_updated`, `practice.matched`, `practice.accepted`,
    `cv.read`, `media.updated`, `station_import.updated`, `message.received`, `coverage`,
    `community_reply`, `debrief`.
    """

    event: str
    data: dict[str, str]


def fan_in_responses(*errors: type[Any]) -> dict[int | str, dict[str, Any]]:
    """Document `/me/events`: many named events on one connection, not one snapshot's frame.

    See `sse_responses` for the single-snapshot case this is the fan-in counterpart of.
    """
    from app.core.errors import error_responses  # avoids an import cycle

    responses = error_responses(*errors)
    responses[200] = {
        "description": (
            "An SSE stream multiplexing this user's own events onto one connection: "
            "`connected`, then a named event (listed on `MeEventEnvelope`) each time something changes, "
            "whose shape is `MeEventEnvelope`, and `ping` every 25 seconds."
        ),
        "content": {SSE_MEDIA_TYPE: {"schema": {"$ref": "#/components/schemas/MeEventEnvelope"}}},
    }
    return responses


def install_me_event_schema(app: FastAPI) -> None:
    """Register `MeEventEnvelope` in the document even though no route uses it as a `response_model`.

    Every other SSE route's frame schema rides along for free because it is also some `GET`'s
    response model. This stream has no snapshot `GET` to borrow a schema from, so its frame
    shape is patched into the built document the same way `install_error_catalogue` patches
    in the error-code enum — otherwise the `$ref` `fan_in_responses` declares would dangle.
    """
    build = app.openapi

    def openapi() -> dict[str, Any]:
        """Build the document as FastAPI would, then add the fan-in frame's schema."""
        spec = build()
        schemas = spec.setdefault("components", {}).setdefault("schemas", {})
        schemas.setdefault("MeEventEnvelope", MeEventEnvelope.model_json_schema())
        return spec

    app.openapi = openapi  # type: ignore[method-assign]
