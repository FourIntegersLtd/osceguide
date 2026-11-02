"""Bringing the consumer station library across.

Two halves, as everywhere else in this package: the transform is pure and
tested on documents shaped like the real ones, and the load is tested against
a real database — because the property that matters is that running it twice
creates nothing, and only Postgres can prove that.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.stations.models import Station, StationVersion
from app.migration.load_stations import load_stations
from app.migration.stations import (
    StationTransformError,
    UnknownLegacyProduct,
    station_from_document,
)
from tests.support.catalog import ensure_exam

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def document(doc_id: str = "sta-1", app_type: str = "sca", **overrides: object) -> dict:
    """A Firestore station, in the shape b2c actually stores one."""
    return {
        "id": doc_id,
        "app_type": app_type,
        "station_name": "Chest pain in a 54-year-old",
        "created_at": "2026-01-15T09:00:00Z",
        "patient_information": {
            "patient_biodata": "Raymond Okafor, 54",
            "gender": "male",
            "opening_sentence": "I've had tightness in my chest since this morning.",
            "persona": "Anxious but polite.",
        },
        "management_plan": {"explanation": "Muscle strain, managed conservatively."},
        **overrides,
    }


class TestTheTransform:
    def test_a_station_keeps_its_exam_its_name_and_its_content(self) -> None:
        station = station_from_document(document())
        assert station.exam_code == "sca"
        assert station.title == "Chest pain in a 54-year-old"
        assert station.content["patient_information"]["gender"] == "male"
        assert station.content["management_plan"]["explanation"]

    def test_the_legacy_id_travels_inside_the_content(self) -> None:
        """So a rendered prompt can still be traced to the document it came
        from after the Firestore project is archived."""
        assert station_from_document(document("abc"))
        assert station_from_document(document("abc")).content["station_id"] == "abc"

    def test_firestore_bookkeeping_is_not_carried_into_the_content(self) -> None:
        station = station_from_document(document(flagged=True, attempts=12, user_id="someone"))
        assert "flagged" not in station.content
        assert "attempts" not in station.content
        assert "user_id" not in station.content

    def test_an_unknown_product_is_refused_rather_than_defaulted(self) -> None:
        # Defaulting to `sca` is how CASC came to be marked with a GP rubric.
        with pytest.raises(UnknownLegacyProduct):
            station_from_document(document(app_type="mrcp"))

    def test_a_document_with_no_id_cannot_become_a_station(self) -> None:
        with pytest.raises(StationTransformError):
            station_from_document({"app_type": "sca", "station_name": "Nameless"})

    def test_a_station_with_no_title_is_named_rather_than_dropped(self) -> None:
        station = station_from_document({"id": "sta-9", "app_type": "plab"})
        assert "sta-9" in station.title

    def test_a_station_with_no_patient_is_imported_and_flagged(self) -> None:
        """Imported anyway: the bootstrap serves a degraded render and refuses
        to freeze it, so the station is visibly broken rather than silently
        missing from the library."""
        station = station_from_document({"id": "sta-8", "app_type": "sca", "station_name": "Thin"})
        assert station.warnings
        assert "degraded" in station.warnings[0]

    def test_content_is_not_reshaped(self) -> None:
        """A migration that rewrites clinical content is how you discover,
        months later, that the station somebody sat is not the one anyone
        wrote."""
        raw = document()
        station = station_from_document(raw)
        for key, value in raw.items():
            if key in {"id", "app_type", "created_at"}:
                continue
            assert station.content[key] == value

    def test_a_numeric_duration_becomes_the_text_its_template_block_takes(self) -> None:
        """Ortho portfolio templates type `duration_minutes` as short text; a
        number imported verbatim made every later save of the station fail."""
        station = station_from_document({"id": "sta-7", "app_type": "ortho", "duration_minutes": 20})
        assert station.content["duration_minutes"] == "20"


@pytest.mark.db
class TestTheLoad:
    async def test_a_station_lands_published_and_runnable(self, db_session: AsyncSession) -> None:
        await ensure_exam(db_session, "sca")
        report, ids = await load_stations(db_session, [station_from_document(document())], now=NOW)

        assert report.stations_created == 1
        assert not report.problems
        version = await db_session.get(StationVersion, ids["sta-1"])
        assert version is not None
        # Published, because they already are: T4 refuses a draft at both
        # attempt creation and bootstrap, so importing into draft would make
        # the whole library unrunnable on the morning of the cutover.
        assert version.status == "published"
        station = await db_session.get(Station, version.station_id)
        assert station is not None
        assert station.owner_kind == "platform"
        assert station.approved is True
        assert station.org_id is None
        assert station.current_version_id == version.id

    async def test_running_it_twice_creates_nothing(self, db_session: AsyncSession) -> None:
        await ensure_exam(db_session, "sca")
        stations = [station_from_document(document())]
        await load_stations(db_session, stations, now=NOW)
        await db_session.flush()

        second, _ = await load_stations(db_session, stations, now=NOW)
        assert second.stations_created == 0
        assert second.stations_existing == 1
        total = await db_session.scalar(select(func.count()).select_from(Station))
        assert total == 1

    async def test_a_station_for_an_exam_nobody_seeded_is_reported(self, db_session: AsyncSession) -> None:
        """Never invented. A station hung off an exam the import made up would
        be marked against a rubric nobody wrote."""
        report, ids = await load_stations(db_session, [station_from_document(document())], now=NOW)
        assert report.stations_created == 0
        assert ids == {}
        assert "seed_platform" in report.problems[0]

    async def test_two_exams_may_have_a_station_of_the_same_name(self, db_session: AsyncSession) -> None:
        # Which is why the legacy id, not the title, is the key.
        await ensure_exam(db_session, "sca")
        await ensure_exam(db_session, "plab")
        report, ids = await load_stations(
            db_session,
            [
                station_from_document(document("sca-1", "sca")),
                station_from_document(document("plab-1", "plab")),
            ],
            now=NOW,
        )
        assert report.stations_created == 2
        assert len(ids) == 2
