"""OpenAPI is the frontend's contract.

Operation ids are derived from the route's tag and function name so the
generated TypeScript client has stable, readable names (`health_get_health`),
and every slice registers a tag here so the document groups by domain.

The document also carries the error vocabulary: `x-codes` on each response
says what that operation can return, and `ErrorResponse.code` is an enum of
every code in the app, so a client switches on values the compiler knows.
"""

from __future__ import annotations

from typing import Any

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


def _org_scoped(route: APIRoute) -> bool:
    """Whether this route resolves an organisation from its slug.

    Read from the resolved dependency graph, not from the endpoint's
    annotations: `from __future__ import annotations` makes those strings, so
    comparing them against `Workspace` matches nothing and silently reports
    every route as unscoped.

    `require_org` returns a closure, so the marker is its qualified name.
    """
    seen = []
    stack = list(route.dependant.dependencies)
    while stack:
        dep = stack.pop()
        call = getattr(dep, "call", None)
        if call is not None:
            seen.append(getattr(call, "__qualname__", ""))
        stack.extend(getattr(dep, "dependencies", ()))
    return any(name.startswith("require_org.") for name in seen)


def document_shared_auth_errors(app: FastAPI) -> None:
    """Declare the codes that shared auth dependencies raise, on the routes that use them.

    `organization_suspended` comes from `require_org`, not from any slice's
    service, so no route lists it in its own `error_responses(...)`. Derived
    from the dependency each route actually uses, so a new org route is
    covered the day it is written rather than needing fifty routes updated
    by hand.

    Written onto `route.responses`, not the finished document, so it and
    `tests/support/declared_codes.py` — which reads the route — agree.
    """
    from app.core.errors import ErrorResponse  # noqa: PLC0415 - avoids an import cycle

    for route in app.routes:
        if not isinstance(route, APIRoute) or not _org_scoped(route):
            continue
        entry = route.responses.setdefault(403, {"model": ErrorResponse, "description": ""})
        codes = entry.setdefault("x-codes", [])
        if ORG_SUSPENDED not in codes:
            codes.append(ORG_SUSPENDED)
            entry["description"] = ", ".join(codes)


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
    from app.core.errors import error_responses  # noqa: PLC0415 - avoids an import cycle

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
    `sse_responses`. `/me/events` multiplexes many differently-shaped events (`attempt`,
    `practice.session_updated`, `cv.read`, `media.updated`, `coverage`, ...) onto one
    connection, so there is no single response model to point at. This envelope documents
    the shape every frame shares instead: the event's name, and a small object of the ids
    naming what changed — never the changed data itself, which the client re-fetches.
    """

    event: str
    data: dict[str, str]


def fan_in_responses(*errors: type[Any]) -> dict[int | str, dict[str, Any]]:
    """Document `/me/events`: many named events on one connection, not one snapshot's frame.

    See `sse_responses` for the single-snapshot case this is the fan-in counterpart of.
    """
    from app.core.errors import error_responses  # noqa: PLC0415 - avoids an import cycle

    responses = error_responses(*errors)
    responses[200] = {
        "description": (
            "An SSE stream multiplexing this user's own events onto one connection: "
            "`connected`, then a named event (`attempt`, `practice.session_updated`, "
            "`cv.read`, `media.updated`, `coverage`, ...) each time something changes, "
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
