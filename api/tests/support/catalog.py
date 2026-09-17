"""Exams for tests, which now have to be written rather than assumed.

Four exams used to be inserted by a migration, so any test that needed one just
read it back by code. The table starts empty now — that is the point of the
change — so a test that needs something to attempt against creates it, the same
way a platform admin would: a rubric, published, then an exam naming it.

`ensure_exam` is the drop-in for the old `catalog.repository.exam_by_code`
reads: it returns the row, creating it the first time it is asked.
"""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import repository as catalog_repository
from app.features.catalog import service_authoring as catalog
from app.features.catalog.models import Exam
from app.features.rubrics import service as rubrics
from tests.support.rubrics import MINIMAL_RUBRIC, PACING, SYSTEM_PROMPT, create_rubric
from tests.support.tokens import bearer

# Roughly the timings the four seeded exams carried, so tests that asserted on
# them keep asserting on something real.
TIMINGS: dict[str, tuple[int, int]] = {
    "sca": (180, 900),
    "plab": (90, 600),
    "casc": (90, 600),
    "ortho": (120, 660),
}


async def ensure_exam(
    session: AsyncSession,
    code: str = "sca",
    *,
    structure: dict[str, Any] | None = None,
    partner_pilot: bool = False,
    published: bool = True,
) -> Exam:
    """The exam with this code, created with a published rubric if it is new.

    Idempotent, so a fixture may call it for the same code more than once.
    """
    existing = await catalog_repository.exam_by_code(session, None, code)
    if existing is not None:
        return existing

    rubric = await rubrics.create_rubric(
        session,
        None,
        title=f"{code} marking rubric",
        structure=structure or MINIMAL_RUBRIC,
        system_prompt=SYSTEM_PROMPT,
        pacing=PACING,
    )
    version_id = rubric.versions[0].id
    await rubrics.publish_version(session, None, rubric.id, 1, actor_id=None, now=_now())
    reading, simulation = TIMINGS.get(code, (90, 600))
    exam = await catalog.create_exam(
        session,
        code=code,
        name=code.upper(),
        default_reading_seconds=reading,
        default_simulation_seconds=simulation,
        rubric_version_id=version_id,
        partner_pilot=partner_pilot,
    )
    if published:
        await catalog.publish_exam(session, exam.id)
    row = await catalog_repository.exam_by_code(session, None, code)
    assert row is not None
    return row


async def create_exam(
    client: AsyncClient,
    admin_token: str,
    *,
    code: str = "sca",
    name: str | None = None,
    structure: dict[str, Any] | None = None,
    partner_pilot: bool = False,
    publish: bool = True,
) -> dict[str, Any]:
    """The same thing over HTTP, as a platform admin actually does it.

    Idempotent on the code, so a test that seeds two organisations does not
    have to know which of them got there first.
    """
    existing = await client.get("/api/v1/exams", headers=bearer(admin_token))
    for exam in existing.json()["items"]:
        if exam["code"] == code:
            return exam

    rubric = await create_rubric(client, admin_token, title=f"{code} marking rubric", structure=structure)
    reading, simulation = TIMINGS.get(code, (90, 600))
    response = await client.post(
        "/api/v1/platform/exams",
        json={
            "code": code,
            "name": name or code.upper(),
            "default_reading_seconds": reading,
            "default_simulation_seconds": simulation,
            "rubric_version_id": rubric["version_id"],
            "partner_pilot": partner_pilot,
        },
        headers=bearer(admin_token),
    )
    assert response.status_code == 201, response.text
    exam = response.json()
    if publish:
        published = await client.post(
            f"/api/v1/platform/exams/{exam['id']}/publish", headers=bearer(admin_token)
        )
        assert published.status_code == 200, published.text
        exam = published.json()
    exam["rubric_id"] = rubric["id"]
    return exam


def _now():  # type: ignore[no-untyped-def]
    from tests.support.fakes import FIXED_NOW

    return FIXED_NOW
