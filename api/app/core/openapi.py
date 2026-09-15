"""OpenAPI is the frontend's contract.

Operation ids are derived from the route's tag and function name so the
generated TypeScript client has stable, readable names (`health_get_health`),
and every slice registers a tag here so the document groups by domain.
"""

from __future__ import annotations

from fastapi.routing import APIRoute

TAGS: list[dict[str, str]] = [
    {"name": "health", "description": "Liveness and dependency checks"},
]


def operation_id(route: APIRoute) -> str:
    tag = route.tags[0] if route.tags else "api"
    return f"{tag}_{route.name}"
