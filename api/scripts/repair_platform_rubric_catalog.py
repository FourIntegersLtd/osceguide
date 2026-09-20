"""Repair a dev DB where SCA skipped seeding and test rubrics were left bound.

Creates the official SCA rubric from ``seeds/platform-starter.json`` when missing,
rebinds the ``sca`` exam and any feedback templates still on junk rubric versions,
then deletes test rubrics (``Platform rubric``, ``sca marking rubric (e2e)``).

    poetry run python scripts/repair_platform_rubric_catalog.py --dry-run
    poetry run python scripts/repair_platform_rubric_catalog.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select, update  # noqa: E402

from app.core.db import get_session_factory, import_all_models  # noqa: E402
from app.features.catalog import repository as catalog_repo  # noqa: E402
from app.features.catalog import service_authoring as exams  # noqa: E402
from app.features.rubrics import service as rubrics  # noqa: E402
from app.features.rubrics.models import FeedbackTemplate, Rubric, RubricVersion  # noqa: E402

OFFICIAL_SCA_TITLE = "Simulated Consultation Assessment marking rubric"
JUNK_RUBRIC_TITLES = frozenset({"Platform rubric", "sca marking rubric (e2e)"})
SEED_PATH = Path(__file__).resolve().parents[1] / "seeds" / "platform-starter.json"
DEFAULT_MARKING_LAYOUT: dict[str, Any] = {
    "schemaVersion": 1,
    "sections": [{"id": "sec_main", "title": "Marking", "blocks": []}],
}


def sca_rubric_spec() -> dict[str, Any]:
    raw = json.loads(SEED_PATH.read_text())
    for entry in raw["exams"]:
        if entry["code"] == "sca":
            return entry["rubric"]
    raise SystemExit(f"{SEED_PATH}: no sca exam entry")


async def platform_rubric_by_title(session, title: str) -> Rubric | None:
    stmt = select(Rubric).where(Rubric.org_id.is_(None), Rubric.title == title)
    return (await session.execute(stmt)).scalar_one_or_none()


async def version_ids_for_rubric(session, rubric_id: uuid.UUID) -> list[uuid.UUID]:
    stmt = select(RubricVersion.id).where(RubricVersion.rubric_id == rubric_id)
    return list((await session.execute(stmt)).scalars())


async def ensure_official_sca_version(session) -> uuid.UUID:
    row = await platform_rubric_by_title(session, OFFICIAL_SCA_TITLE)
    if row is None:
        spec = sca_rubric_spec()
        created = await rubrics.create_rubric(
            session,
            None,
            title=spec["title"],
            structure=spec["structure"],
            system_prompt=spec["system_prompt"],
            pacing=spec["pacing"],
            marking_layout=spec.get("marking_layout") or DEFAULT_MARKING_LAYOUT,
        )
        published = await rubrics.publish_version(
            session, None, created.id, 1, actor_id=None, now=datetime.now(UTC)
        )
        return uuid.UUID(str(published.id))

    if row.current_version_id is None:
        raise SystemExit(f"Rubric {OFFICIAL_SCA_TITLE!r} exists but has no current_version_id")
    return row.current_version_id


async def repair(*, dry_run: bool) -> int:
    import_all_models()
    sca_version_id: uuid.UUID | None = None
    junk_version_ids: list[uuid.UUID] = []
    actions: list[str] = []

    factory = get_session_factory()
    async with factory() as session, session.begin():
        sca_version_id = await ensure_official_sca_version(session)
        actions.append(f"SCA rubric version: {sca_version_id}")

        sca_exam = await catalog_repo.exam_by_code(session, None, "sca")
        if sca_exam is None:
            raise SystemExit("No platform exam with code 'sca'")
        if sca_exam.rubric_version_id != sca_version_id:
            actions.append(f"Rebind exam sca: {sca_exam.rubric_version_id} -> {sca_version_id}")
            await exams.update_exam(session, sca_exam.id, None, rubric_version_id=sca_version_id)
        else:
            actions.append("Exam sca already bound to official SCA rubric")

        junk_rows = list(
            (
                await session.execute(
                    select(Rubric).where(Rubric.org_id.is_(None), Rubric.title.in_(JUNK_RUBRIC_TITLES))
                )
            ).scalars()
        )
        for junk in junk_rows:
            junk_version_ids.extend(await version_ids_for_rubric(session, junk.id))

        if junk_version_ids:
            stmt = (
                select(FeedbackTemplate)
                .where(FeedbackTemplate.rubric_version_id.in_(junk_version_ids))
                .order_by(FeedbackTemplate.title, FeedbackTemplate.id)
            )
            templates = list((await session.execute(stmt)).scalars())
            for template in templates:
                actions.append(
                    f"Rebind feedback template {template.title!r} ({template.id}): "
                    f"{template.rubric_version_id} -> {sca_version_id}"
                )
            await session.execute(
                update(FeedbackTemplate)
                .where(FeedbackTemplate.rubric_version_id.in_(junk_version_ids))
                .values(rubric_version_id=sca_version_id)
            )

        for junk in junk_rows:
            actions.append(f"Delete rubric {junk.title!r} ({junk.id})")
        if junk_rows:
            await session.execute(delete(Rubric).where(Rubric.id.in_([r.id for r in junk_rows])))

        if dry_run:
            for line in actions:
                print(line)  # noqa: T201
            print("dry-run (rolled back — no changes committed)")  # noqa: T201
            raise _Rollback()

    for line in actions:
        print(line)  # noqa: T201
    print("committed")  # noqa: T201
    return 0


class _Rollback(Exception):
    """Rollback the transaction after recording actions."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print actions without committing")
    args = parser.parse_args()
    try:
        return asyncio.run(repair(dry_run=args.dry_run))
    except _Rollback:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
