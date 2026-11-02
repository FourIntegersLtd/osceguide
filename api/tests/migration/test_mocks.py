"""A legacy mock must arrive as a session its owner can see, once, with the stations that exist."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.station_sets.models import StationSet, StationSetEntry
from app.migration import b2c_lookups, loader
from app.migration.load_b2c_mocks import load_mocks
from app.migration.load_stations import load_stations
from app.migration.stations import station_from_document
from app.migration.users import merge_users
from tests.migration.test_loader import b2c_user
from tests.migration.test_station_import import document
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db


def _mock(**overrides: object) -> dict:
    """A Firestore mock with one station in the library and one that is not."""
    return {
        "id": "doc-1",
        "mock_id": "mock-1",
        "app_type": "sca",
        "created_by": "fs-1",
        "name": "Session 7",
        "created_at": "2026-06-21T21:43:56.758236Z",
        "locked": False,
        "completed": False,
        "stations": [
            {"station_id": "sta-1", "attempts": 2, "debrief_attempts": 1},
            {"station_id": "gone", "attempts": 1},
        ],
        **overrides,
    }


async def _ready(session: AsyncSession):  # type: ignore[no-untyped-def]
    """One user and one library station; returns the lookups."""
    await ensure_exam(session, "sca")
    await loader.load_users(session, merge_users([b2c_user("alice@example.com", "sca", "fs-1")]))
    await load_stations(session, [station_from_document(document())], now=datetime(2026, 9, 16, tzinfo=UTC))
    await session.flush()
    return await b2c_lookups.build(session)


async def test_a_mock_becomes_a_session_with_its_run_counts(db_session: AsyncSession) -> None:
    lookups = await _ready(db_session)

    report = await load_mocks(db_session, [_mock()], lookups)

    assert report.counts["sessions created"] == 1
    assert report.counts["mock stations not in the library (left out)"] == 1
    station_set = (await db_session.scalars(select(StationSet))).one()
    assert station_set.name == "Session 7"
    entry = (await db_session.scalars(select(StationSetEntry))).one()
    assert (entry.attempts, entry.debrief_attempts) == (2, 1)


async def test_loading_twice_adds_nothing(db_session: AsyncSession) -> None:
    lookups = await _ready(db_session)
    await load_mocks(db_session, [_mock()], lookups)

    second = await load_mocks(db_session, [_mock()], lookups)

    assert second.counts["sessions already there"] == 1
    assert await db_session.scalar(select(func.count()).select_from(StationSet)) == 1
    assert await db_session.scalar(select(func.count()).select_from(StationSetEntry)) == 1


async def test_a_mock_of_an_unknown_owner_is_skipped(db_session: AsyncSession) -> None:
    lookups = await _ready(db_session)

    report = await load_mocks(db_session, [_mock(created_by="nobody")], lookups)

    assert report.counts["mocks skipped (owner or exam not imported)"] == 1
    assert await db_session.scalar(select(func.count()).select_from(StationSet)) == 0


async def test_attempts_are_hung_on_their_session_station(db_session: AsyncSession) -> None:
    """A transcript that names a mock and station is linked, so the session's review shows it."""
    from sqlalchemy import select

    from app.features.attempts.models import Attempt
    from app.migration import loader
    from app.migration.attempts import attempt_from_transcript
    from app.migration.b2c_lookups import build
    from app.migration.load_b2c_mocks import link_attempts_to_sessions
    from tests.migration.test_loader import b2c_transcript

    lookups = await _ready(db_session)
    mock = _mock()
    await load_mocks(db_session, [mock], lookups)
    transcript = {
        **b2c_transcript("fs-1", "t-1", turns=2),
        "app_type": "sca",
        "mock_id": mock["mock_id"],
        "station_id": mock["stations"][0]["station_id"],
    }
    await loader.load_attempts(
        db_session, [attempt_from_transcript(transcript, app_type="sca")], user_ids=lookups.users
    )

    report = await link_attempts_to_sessions(db_session, [mock], [transcript], await build(db_session))

    assert report.counts["attempts linked to their session"] == 1
    attempt = await db_session.scalar(select(Attempt).where(Attempt.legacy_ref.is_not(None)))
    assert (attempt.kind, attempt.set_entry_id is not None) == ("set_station", True)
