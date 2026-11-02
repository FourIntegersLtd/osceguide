"""An editor's worklist: every published platform-library station nobody has approved yet.

Read-only, no side effects. `approved` gates a published station from a normal reader of the
library until an editor has reviewed it (see the migration `7b2f6a1d4e9c_stations_approved.py`
and `app/features/stations/repository_library.py`'s `require_approved`); this just lists what is
sitting behind that gate so an editor knows what to look at.

    poetry run python scripts/report_unapproved_stations.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402

from app.core.db import get_session_factory, import_all_models  # noqa: E402
from app.features.catalog.service import exam_codes_by_id  # noqa: E402
from app.features.stations.models import Station, StationVersion  # noqa: E402


async def unapproved_published_stations() -> list[tuple[Station, str, datetime | None]]:
    """Every `published`, unapproved platform-library station, with its exam code and when it
    was first published (the earliest `published_at` across its versions, `None` if that is
    somehow missing)."""
    factory = get_session_factory()
    async with factory() as session:
        first_published_at = (
            select(func.min(StationVersion.published_at))
            .where(StationVersion.station_id == Station.id)
            .correlate(Station)
            .scalar_subquery()
        )
        stmt = (
            select(Station, first_published_at)
            .where(
                Station.owner_kind == "platform",
                Station.status == "published",
                Station.approved.is_(False),
            )
            .order_by(first_published_at.asc())
        )
        rows = (await session.execute(stmt)).all()
        codes = await exam_codes_by_id(session, [station.exam_id for station, _ in rows])
        return [
            (station, codes.get(station.exam_id, ""), first_published) for station, first_published in rows
        ]


async def main() -> int:
    import_all_models()
    rows = await unapproved_published_stations()
    if not rows:
        print("Nothing to review: every published station is approved.")  # noqa: T201
        return 0
    print(f"{len(rows)} published station(s) awaiting approval:\n")  # noqa: T201
    for station, exam_code, first_published_at in rows:
        print(  # noqa: T201
            f"  {station.id}  [{exam_code or 'unknown exam'}]  {station.title!r}"
            f"  first published {first_published_at or 'unknown'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
