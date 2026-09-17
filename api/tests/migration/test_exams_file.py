"""The exams an import references have to be declared, not assumed.

Four exams were inserted by a migration, so the importer could take them for
granted. It cannot now — and the failure mode if it tried would be the worst
kind: a partial import of somebody's history, discovered halfway through.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import repository as catalog_repository
from app.migration import exams as exam_loader
from tests.support.rubrics import MINIMAL_RUBRIC, PACING, SYSTEM_PROMPT

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def spec(*codes: str) -> dict:
    return {
        "exams": [
            {
                "code": code,
                "name": code.upper(),
                "default_reading_seconds": 90,
                "default_simulation_seconds": 600,
                "rubric": {
                    "title": f"{code} rubric",
                    "structure": MINIMAL_RUBRIC,
                    "system_prompt": SYSTEM_PROMPT,
                    "pacing": PACING,
                },
            }
            for code in codes
        ]
    }


async def test_the_file_creates_and_publishes_each_exam(db_session: AsyncSession) -> None:
    created = await exam_loader.load_exams(db_session, spec("sca", "plab"), now=NOW)

    assert sorted(created) == ["plab", "sca"]
    for exam in created.values():
        assert exam.status == "published"
        assert exam.rubric_version_id is not None, "and it names what it is marked against"


async def test_running_it_twice_changes_nothing(db_session: AsyncSession) -> None:
    """A second import must not quietly re-mark anybody."""
    first = await exam_loader.load_exams(db_session, spec("sca"), now=NOW)
    second = await exam_loader.load_exams(db_session, spec("sca"), now=NOW)

    assert first["sca"].id == second["sca"].id
    assert first["sca"].rubric_version_id == second["sca"].rubric_version_id


async def test_an_exam_with_no_rubric_is_refused(db_session: AsyncSession) -> None:
    """An exam that cannot be marked cannot be published, and its imported
    attempts would have nothing to be re-marked against."""
    broken = {
        "exams": [
            {
                "code": "sca",
                "name": "SCA",
                "default_reading_seconds": 90,
                "default_simulation_seconds": 600,
            }
        ]
    }

    with pytest.raises(exam_loader.InvalidExamsFile, match="no rubric"):
        await exam_loader.load_exams(db_session, broken, now=NOW)


async def test_an_empty_file_is_refused(db_session: AsyncSession) -> None:
    with pytest.raises(exam_loader.InvalidExamsFile):
        await exam_loader.load_exams(db_session, {"exams": []}, now=NOW)


async def test_nothing_is_written_when_the_rubric_cannot_be_marked_against(
    db_session: AsyncSession,
) -> None:
    broken = spec("sca")
    broken["exams"][0]["rubric"]["structure"] = {"scale": [], "domains": []}

    with pytest.raises(Exception):  # noqa: B017 - the refusal's type is the service's, not ours
        await exam_loader.load_exams(db_session, broken, now=NOW)

    assert await catalog_repository.exam_by_code(db_session, "sca") is None


def test_an_exam_the_export_needs_and_the_file_omits_is_named() -> None:
    """Checked before anything is written, so a missing exam is not discovered
    halfway through somebody's history."""
    missing = exam_loader.missing_exams(spec("sca"), {"sca", "plab", "casc"})

    assert missing == ["casc", "plab"]


def test_nothing_is_missing_when_the_file_covers_the_export() -> None:
    assert exam_loader.missing_exams(spec("sca", "plab"), {"sca"}) == []
