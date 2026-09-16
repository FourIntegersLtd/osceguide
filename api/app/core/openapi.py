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

from app.core.errors import error_codes

TAGS: list[dict[str, str]] = [
    {"name": "health", "description": "Liveness and dependency checks"},
    {"name": "identity", "description": "Accounts, sessions and passwords"},
    {"name": "tenancy", "description": "Organisations, membership and access"},
    {"name": "catalog", "description": "Exams and the programmes that offer them"},
    {"name": "stations", "description": "Scenarios and the templates behind them"},
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
    {"name": "marketplace", "description": "Peer practice slots offered and claimed"},
    {"name": "peer-practice", "description": "Being matched with somebody to practise"},
    {"name": "growth", "description": "Partner attribution and referrals"},
    {"name": "media", "description": "Slides, summaries, blogs and podcasts"},
    {"name": "assistant", "description": "Help, onboarding and demonstration sessions"},
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


def install_error_catalogue(app: FastAPI) -> None:
    """Publish the error-code enum into `ErrorResponse` as the document is built.

    Done by wrapping `app.openapi` rather than annotating the model, because
    the codes live on `AppError` subclasses across every slice and those are
    not imported when `core.errors` defines the model. By the time a document
    is asked for, every router — and so every slice's `errors.py` — is loaded.
    """
    build = app.openapi

    def openapi() -> dict[str, Any]:
        spec = build()
        schema = spec.get("components", {}).get("schemas", {}).get("ErrorResponse")
        if schema is not None:
            schema["properties"]["code"]["enum"] = error_codes()
        return spec

    app.openapi = openapi  # type: ignore[method-assign]
