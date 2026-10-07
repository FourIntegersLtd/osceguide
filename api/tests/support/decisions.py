"""Taking a candidate's decision through the result workflow, for tests that need one settled."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from tests.support.tokens import bearer

EVIDENCE = {"slots": ["a", "b"], "scores": {"communication": "G"}}


async def settle_decision(
    client: AsyncClient,
    admin: str,
    *,
    org_slug: str,
    sitting_id: uuid.UUID | str,
    trainee_id: uuid.UUID | str,
    release: bool = False,
) -> str:
    """Record a pass and sign it off; release it too when asked. Returns the decision's URL."""
    decision = f"/api/v1/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/decision"
    drafted = await client.put(
        decision,
        json={
            "assessment_outcome": "pass",
            "rationale": "Met the standard.",
            "evidence": EVIDENCE,
            "expected_revision": 0,
        },
        headers=bearer(admin),
    )
    assert drafted.status_code == 200, drafted.text
    signed = await client.post(f"{decision}/sign-off", headers=bearer(admin))
    assert signed.status_code == 200, signed.text
    if release:
        released = await client.post(
            f"{decision}/release", json={"evidence": EVIDENCE}, headers=bearer(admin)
        )
        assert released.status_code == 200, released.text
    return decision
