"""Bringing the consumer station library across."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.stations.models import Station, StationVersion
from app.migration.load_stations import load_stations
from app.migration.stations import (
    MigratedStation,
    StationTransformError,
    UnknownLegacyProduct,
    station_from_document,
)

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def document(doc_id: str = "sta-1", app_type: str = "sca", **overrides: object) -> dict:
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
        assert station_from_document(document("abc")).content["station_id"] == "abc"

    def test_firestore_bookkeeping_is_not_carried_into_the_content(self) -> None:
        station = station_from_document(document(flagged=True, attempts=12, user_id="someone"))
        assert "flagged" not in station.content
        assert "attempts" not in station.content
        assert "user_id" not in station.content

    def test_an_unknown_product_is_refused_rather_than_defaulted(self) -> None:
        with pytest.raises(UnknownLegacyProduct):
            station_from_document(document(app_type="mrcp"))

    def test_a_document_with_no_id_cannot_become_a_station(self) -> None:
        with pytest.raises(StationTransformError):
            station_from_document({"app_type": "sca", "station_name": "Nameless"})

    def test_a_station_with_no_title_is_named_rather_than_dropped(self) -> None:
        station = station_from_document({"id": "sta-9", "app_type": "plab"})
        assert "sta-9" in station.title

    def test_a_station_with_no_patient_is_imported_and_flagged(self) -> None:
        station = station_from_document({"id": "sta-8", "app_type": "sca", "station_name": "Thin"})
        assert station.warnings
        assert "degraded" in station.warnings[0]

    def test_content_is_not_reshaped(self) -> None:
        raw = document()
        station = station_from_document(raw)
        for key, value in raw.items():
            if key in {"id", "app_type", "created_at"}:
                continue
            assert station.content[key] == value


@pytest.mark.db
class TestTheLoad:
    async def test_a_station_lands_published_and_runnable(self, db_session: AsyncSession) -> None:
        report, ids = await load_stations(db_session, [station_from_document(document())], now=NOW)

        assert report.stations_created == 1
        assert not report.problems
        version = await db_session.get(StationVersion, ids["sta-1"])
        assert version is not None
        assert version.status == "published"
        station = await db_session.get(Station, version.station_id)
        assert station is not None
        assert station.owner_kind == "platform"
        assert station.org_id is None
        assert station.current_version_id == version.id

    async def test_running_it_twice_creates_nothing(self, db_session: AsyncSession) -> None:
        stations = [station_from_document(document())]
        await load_stations(db_session, stations, now=NOW)
        await db_session.flush()

        second, _ = await load_stations(db_session, stations, now=NOW)
        assert second.stations_created == 0
        assert second.stations_existing == 1
        total = await db_session.scalar(select(func.count()).select_from(Station))
        assert total == 1

    async def test_a_station_for_an_unknown_exam_is_reported(self, db_session: AsyncSession) -> None:
        missing = MigratedStation(
            legacy_id="orphan-1",
            exam_code="not-a-real-exam",
            title="Orphan",
            content={"station_id": "orphan-1"},
        )
        report, ids = await load_stations(db_session, [missing], now=NOW)
        assert report.stations_created == 0
        assert ids == {}
        assert "alembic upgrade head" in report.problems[0]

    async def test_two_exams_may_have_a_station_of_the_same_name(self, db_session: AsyncSession) -> None:
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
