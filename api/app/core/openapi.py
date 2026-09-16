"""OpenAPI is the frontend's contract.

Operation ids are derived from the route's tag and function name so the
generated TypeScript client has stable, readable names (`health_get_health`),
and every slice registers a tag here so the document groups by domain.
"""

from __future__ import annotations

from fastapi.routing import APIRoute

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
    tag = route.tags[0] if route.tags else "api"
    # Hyphens are fine in a tag and awkward in a generated method name, so
    # `peer-practice` becomes `peer_practice_join_queue`.
    return f"{tag.replace('-', '_')}_{route.name}"
