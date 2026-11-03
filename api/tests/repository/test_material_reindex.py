"""Building the index out of what is published, and retiring what is not.

The failure this file exists to prevent is the quiet one: a summary withdrawn
by its author, still in the index, still being read out by the tutor, with a
citation to a page that now returns a 404. Nothing downstream notices — the
answer is fluent and the doctor has no way to tell.

The index is faked, because which passage is nearest is `test_material_index`'s
question. What is asked here is which *sources* are offered to it.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import repository as identity_repo
from app.features.media import service as media
from app.features.media_production import service_storage
from app.features.stations import repository as stations_repo
from app.features.tutor_memory import service_material
from tests.support.catalog import ensure_exam
from tests.support.fakes import FakeMaterialIndex, FakeVectorIndex

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)

# Long enough that the chunker's section pass has something to cut at, so the
# test exercises the path the real material takes rather than a one-liner.
PLAN = {
    "management_plan": {
        "assessment": "Rule out an acute coronary syndrome before anything else.",
        "red_flags": "Pain radiating to the jaw, sweating, or a pain that woke them.",
        "follow_up": "Review in two weeks, sooner if the pain changes in character.",
    },
    # Never indexed: this is what the station assesses.
    "patient_information": {"patient_biodata": "Raymond Okafor, 54, a school receptionist"},
}


def station_passages(index: FakeMaterialIndex) -> list:  # type: ignore[type-arg]
    """The station passages alone; every run also indexes the help articles."""
    return [passage for passage in index.passages if passage.corpus == service_material.STATION_CORPUS]


async def published_station(
    db_session: AsyncSession,
    *,
    exam_code: str = "sca",
    title: str = "Chest pain",
    content: dict[str, object] | None = None,
) -> uuid.UUID:
    exam = await ensure_exam(db_session, exam_code)
    assert exam is not None
    author = await identity_repo.create_user(
        db_session, email=f"a{uuid.uuid4().hex[:8]}@example.com", name="A", password_hash=None
    )
    station = await stations_repo.create_station(db_session, None, exam_id=exam.id, title=title)
    version = await stations_repo.add_version(
        db_session, None, station_id=station.id, version=1, content=content or PLAN
    )
    await stations_repo.set_version_status(
        db_session, None, version.id, status="published", at=NOW, by=author.id
    )
    await stations_repo.set_current_version(db_session, None, station.id, version_id=version.id)
    # An unapproved station is not in the library, so it is not in the tutor's material either.
    await stations_repo.set_station_approved(db_session, None, station.id, approved=True)
    await db_session.flush()
    return version.id


async def test_a_published_station_is_indexed_by_its_management_plan(
    db_session: AsyncSession,
) -> None:
    version_id = await published_station(db_session)
    index = FakeMaterialIndex()

    await service_material.reindex(db_session, index=index)

    indexed = " ".join(p.text for p in station_passages(index))
    assert "acute coronary syndrome" in indexed
    assert {p.source_id for p in station_passages(index)} == {str(version_id)}


async def test_a_station_never_offers_the_material_it_assesses(
    db_session: AsyncSession,
) -> None:
    """The patient brief is the answers. Indexing it hands them over on request."""
    await published_station(db_session)
    index = FakeMaterialIndex()

    await service_material.reindex(db_session, index=index)

    indexed = " ".join(p.text for p in index.passages)
    assert "Raymond Okafor" not in indexed
    assert "school receptionist" not in indexed


async def test_a_station_with_no_management_plan_is_skipped_rather_than_stripped(
    db_session: AsyncSession,
) -> None:
    """Contributing nothing beats contributing the patient brief."""
    await published_station(
        db_session, title="Nothing to read", content={"patient_information": {"x": "secret"}}
    )
    index = FakeMaterialIndex()

    await service_material.reindex(db_session, index=index)

    assert station_passages(index) == []


async def test_a_draft_station_is_not_indexed(db_session: AsyncSession) -> None:
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    station = await stations_repo.create_station(db_session, None, exam_id=exam.id, title="Draft")
    await stations_repo.add_version(db_session, None, station_id=station.id, version=1, content=PLAN)
    await db_session.flush()
    index = FakeMaterialIndex()

    await service_material.reindex(db_session, index=index)

    assert station_passages(index) == []


async def test_help_articles_are_indexed_for_every_exam_or_under_their_own(
    db_session: AsyncSession,
) -> None:
    """An article for every exam carries none; one written for SCA reaches SCA holders only.

    An article for an exam this deployment does not have (ortho, here) is left out
    rather than indexed as if it were for everyone.
    """
    sca = await ensure_exam(db_session, "sca")
    assert sca is not None
    index = FakeMaterialIndex()

    await service_material.reindex(db_session, index=index)

    assert index.exam_of[("help", "first-steps")] is None
    assert index.exam_of[("help", "practice-with-people@sca")] == str(sca.id)
    assert not any(source_id.startswith("ortho-cv") for _, source_id in index.exam_of)


async def test_reindex_media_item_indexes_one_source_and_leaves_others(
    db_session: AsyncSession,
) -> None:
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    author = await identity_repo.create_user(
        db_session, email=f"o{uuid.uuid4().hex[:8]}@example.com", name="O", password_hash=None
    )
    kept = await media.create(
        db_session,
        kind="blog",
        title="Already indexed",
        summary="An older blog post.",
        content={"body": "Keep this passage in the index."},
        exam_code="sca",
        author_id=author.id,
    )
    await media.publish(db_session, kept.id, index=FakeVectorIndex(), now=NOW)
    index = FakeMaterialIndex()
    await service_material.reindex(db_session, index=index)
    before = len(index.passages)

    fresh = await media.create(
        db_session,
        kind="summary",
        title="New summary",
        summary="Indexed on its own.",
        content={"body": "Only this summary should be added now."},
        exam_code="sca",
        author_id=author.id,
    )
    await media.publish(db_session, fresh.id, index=FakeVectorIndex(), now=NOW)

    added = await service_material.reindex_media_item(db_session, fresh.id, index=index)

    assert added == 1
    assert len(index.passages) == before + added
    assert any(p.source_id == str(kept.id) for p in index.passages)
    assert any("Only this summary" in p.text for p in index.passages)


async def test_published_media_is_indexed_with_its_exam(db_session: AsyncSession) -> None:
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    author = await identity_repo.create_user(
        db_session, email=f"m{uuid.uuid4().hex[:8]}@example.com", name="M", password_hash=None
    )
    item = await media.create(
        db_session,
        kind="summary",
        title="Anxiety",
        summary="A short summary of generalised anxiety.",
        content={"body": "Offer a talking therapy or a medicine, and say both work."},
        exam_code="sca",
        author_id=author.id,
    )
    # The media slice's own search index, which is a different port from the
    # tutor's — `publish` writes to it, and this test is about the other one.
    await media.publish(db_session, item.id, index=FakeVectorIndex(), now=NOW)
    await db_session.flush()
    index = FakeMaterialIndex()

    await service_material.reindex(db_session, index=index)

    summaries = [p for p in index.passages if p.corpus == "summary"]
    assert summaries, "the published summary was not indexed"
    assert index.exam_of[("summary", str(item.id))] == str(exam.id)


async def test_running_it_twice_changes_nothing(db_session: AsyncSession) -> None:
    """Idempotent by construction, which is what makes a retry safe."""
    await published_station(db_session)
    index = FakeMaterialIndex()

    first = await service_material.reindex(db_session, index=index)
    after_first = [(p.corpus, p.source_id, p.text) for p in index.passages]
    second = await service_material.reindex(db_session, index=index)

    assert (second.sources, second.passages) == (first.sources, first.passages)
    assert [(p.corpus, p.source_id, p.text) for p in index.passages] == after_first


async def test_material_that_is_no_longer_published_is_retired(db_session: AsyncSession) -> None:
    """The quiet failure: a withdrawn document still being quoted.

    Nothing downstream notices. The answer is fluent, the citation looks right,
    and it points at a page that now returns a 404.
    """
    index = FakeMaterialIndex()
    await index.upsert(
        corpus="summary",
        source_id="withdrawn",
        exam_id=str(uuid.uuid4()),
        title="Taken down last week",
        chunks=[{"index": 0, "section": "management", "text": "Advice nobody may read now."}],
    )
    await published_station(db_session)

    run = await service_material.reindex(db_session, index=index)

    assert run.retired == 1
    assert "withdrawn" not in {p.source_id for p in index.passages}
    assert await index.indexed_sources(corpus="summary") == set()


async def test_material_that_is_still_published_is_not_retired(db_session: AsyncSession) -> None:
    """The other half: a re-index must not empty the index it just filled."""
    version_id = await published_station(db_session)
    index = FakeMaterialIndex()

    await service_material.reindex(db_session, index=index)
    second = await service_material.reindex(db_session, index=index)

    assert second.retired == 0
    assert await index.indexed_sources(corpus="station") == {str(version_id)}


async def test_an_unconfigured_deployment_retires_nothing(db_session: AsyncSession) -> None:
    """A nightly run without an embedding key must not empty a real index.

    `NoMaterialIndex` reports holding nothing rather than reporting the table's
    contents, so the retire pass has nothing to act on. The opposite — treating
    "I cannot see it" as "it is not there" — would have one misconfigured
    replica delete every passage the configured ones wrote.
    """
    from app.features.tutor_memory.index import NoMaterialIndex

    await published_station(db_session)

    run = await service_material.reindex(db_session, index=NoMaterialIndex())

    assert (run.passages, run.retired) == (0, 0)


async def test_a_failing_embedder_says_it_cannot_look_it_up(db_session: AsyncSession) -> None:
    """The embedding API being down is not evidence about the material.

    "Nothing found" would have the tutor assert, in a clinical conversation,
    that the reading does not cover something it never managed to read.
    """
    from app.features.entitlements import repository as ent_repo
    from app.features.tutor_memory import service_search as ss
    from app.features.tutor_memory.embedder import EmbeddingFailed

    class BrokenIndex(FakeMaterialIndex):
        async def search(self, **kwargs):  # type: ignore[no-untyped-def]
            raise EmbeddingFailed("the embedding API refused the request")

    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    user = await identity_repo.create_user(
        db_session, email=f"e{uuid.uuid4().hex[:8]}@example.com", name="E", password_hash=None
    )
    await ent_repo.grant(
        db_session,
        user_id=user.id,
        exam_id=exam.id,
        source="purchase",
        ends_at=datetime.now(UTC) + timedelta(days=30),
    )
    await db_session.flush()

    answer = await ss.answer_question(
        db_session,
        user_id=user.id,
        query="safety net chest pain",
        corpus=None,
        index=BrokenIndex(),
        now=datetime.now(UTC),
    )

    assert answer.result == ss.NOT_CONFIGURED
    assert answer.display is None


async def test_a_media_items_signed_links_never_reach_the_index(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A body reads back with working two-hour file links; the tutor must be told the words, not the links."""
    settings = SimpleNamespace(
        aws_s3_bucket="osceguide",
        aws_region="eu-west-2",
        aws_access_key_id="AKIAFAKE",
        aws_secret_access_key="fake",  # noqa: S106
    )
    monkeypatch.setattr(service_storage, "get_settings", lambda: settings)
    await ensure_exam(db_session, "sca")
    author = await identity_repo.create_user(
        db_session, email=f"l{uuid.uuid4().hex[:8]}@example.com", name="L", password_hash=None
    )
    link = "https://osceguide.s3.eu-west-2.amazonaws.com/teaching_videos/sca/angina_1.mp4"
    item = await media.create(
        db_session,
        kind="summary",
        title="Angina",
        summary="A short summary.",
        content={"body": f"Watch ![clip]({link}) for the walk-through.", "final_video_url": link},
        exam_code="sca",
        author_id=author.id,
    )
    await media.publish(db_session, item.id, index=FakeVectorIndex(), now=NOW)
    index = FakeMaterialIndex()

    await service_material.reindex_media_item(db_session, item.id, index=index)

    indexed = " ".join(passage.text for passage in index.passages if passage.source_id == str(item.id))
    assert "walk-through" in indexed
    assert "amazonaws" not in indexed and "X-Amz" not in indexed
