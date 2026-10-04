"""The voice tutor's lookup: our material first, the guideline library behind it."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import GuidelinePassage, Passage
from app.features.identity import repository as identity_repo
from app.features.tutor_memory import service_search as ss
from tests.support.fakes import FakeGuidelineIndex, FakeMaterialIndex

pytestmark = pytest.mark.db

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
NICE = GuidelinePassage(source="NICE NG136", text="Offer an ACE inhibitor under 55.", score=0.9)


def help_index() -> FakeMaterialIndex:
    """Material anybody may read, so no entitlement has to be set up to find it."""
    index = FakeMaterialIndex()
    index.passages.append(
        Passage(
            corpus="help", source_id="booking", title="Booking", text="hypertension", section="", score=1.0
        )
    )
    return index


async def ask(db_session: AsyncSession, query: str, **kwargs: object):  # type: ignore[no-untyped-def]
    user = await identity_repo.create_user(
        db_session, email=f"g{uuid.uuid4().hex[:8]}@example.com", name="G", password_hash=None
    )
    return await ss.answer_question(db_session, user_id=user.id, query=query, now=NOW, **kwargs)  # type: ignore[arg-type]


async def test_guidelines_follow_the_material_and_stay_off_the_card(db_session: AsyncSession) -> None:
    guidelines = FakeGuidelineIndex([NICE])

    answer = await ask(db_session, "hypertension", corpus=None, index=help_index(), guidelines=guidelines)

    assert answer.result.index("Here is what the material says") < answer.result.index("[NICE NG136] Offer")
    assert "Clinical guidelines, the second line." in answer.result
    assert [citation["title"] for citation in answer.display["citations"]] == ["Booking"]
    assert guidelines.searches == [("hypertension", ss.GUIDELINE_LIMIT, True)]


async def test_guidelines_answer_when_the_material_has_nothing(db_session: AsyncSession) -> None:
    answer = await ask(
        db_session, "ace inhibitor", corpus=None, index=help_index(), guidelines=FakeGuidelineIndex([NICE])
    )

    assert answer.result.startswith("Their own material has nothing on that")
    assert "[NICE NG136] Offer an ACE inhibitor under 55." in answer.result
    assert answer.display is None


async def test_nothing_in_either_says_the_reading_does_not_cover_it(db_session: AsyncSession) -> None:
    answer = await ask(
        db_session, "gardening", corpus=None, index=help_index(), guidelines=FakeGuidelineIndex()
    )

    assert answer.result == ss.NOTHING_IN_MATERIAL


async def test_a_slow_guideline_library_is_left_out_rather_than_waited_for(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ss, "GUIDELINE_TIMEOUT_SECONDS", 0.05)

    answer = await ask(
        db_session,
        "hypertension",
        corpus=None,
        index=help_index(),
        guidelines=FakeGuidelineIndex([NICE], delay=5),
    )

    assert "Here is what the material says" in answer.result
    assert "NICE" not in answer.result


async def test_a_question_about_the_app_does_not_ask_the_guidelines(db_session: AsyncSession) -> None:
    guidelines = FakeGuidelineIndex([NICE])

    await ask(db_session, "hypertension", corpus="help", index=help_index(), guidelines=guidelines)

    assert guidelines.searches == []
