"""One token per kind of caller, and the two assertions every role matrix repeats."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from httpx import AsyncClient

from app.core.auth import Membership
from tests.support.sittings import org_with_admin
from tests.support.tokens import bearer


@dataclass(frozen=True)
class Callers:
    """`tokens[role]` is the raw token; `callers[role]` the headers carrying it.

    `anonymous` has no token. `stranger` belongs to no organisation. `partner_admin` is an
    org admin without being an institution admin.
    """

    tokens: dict[str, str]

    def __getitem__(self, role: str) -> dict[str, str]:
        return bearer(self.tokens[role]) if role in self.tokens else {}


async def callers(client: AsyncClient, make_actor, slug: str = "kings") -> Callers:  # type: ignore[no-untyped-def]
    org_id, owner = await org_with_admin(client, make_actor, slug)

    async def member(role: str) -> str:
        return await make_actor(
            f"{role}-{slug}@example.com",
            memberships=(Membership(org_id=org_id, org_slug=slug, role=role),),
            active_org_slug=slug,
        )

    return Callers(
        tokens={
            "stranger": await make_actor(f"stranger-{slug}@example.com"),
            "trainee": await member("trainee"),
            "supervisor": await member("supervisor"),
            "partner_admin": await member("partner_admin"),
            "owner": owner,
            "platform": await make_actor(f"platform-{slug}@example.com", platform_admin=True),
        }
    )


async def assert_unauthenticated(client: AsyncClient, method: str, path: str, body: Any = None) -> None:
    response = await client.request(method, path, json=body)
    assert (response.status_code, response.json()["code"]) == (401, "unauthenticated"), (path, response.text)


async def refused(
    client: AsyncClient, headers: dict[str, str], method: str, path: str, body: Any = None
) -> None:
    response = await client.request(method, path, json=body, headers=headers)
    assert (response.status_code, response.json()["code"]) == (403, "forbidden"), (path, response.text)
