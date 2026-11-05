"""The help chat: this learner's stations and summaries first, clinical guidelines second."""

import contextlib
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import openai
import pytest

from app.core.ports import GuidelinePassage, Passage
from app.features.assistant import service_knowledge as service
from app.features.assistant.schemas import KnowledgeChat
from tests.support.fakes import FakeGuidelineIndex, FakeMaterialIndex

NICE = GuidelinePassage(source="NICE NG136", text="Offer an ACE inhibitor under 55.", score=0.9)


def material(sca: object, plab: object) -> FakeMaterialIndex:
    index = FakeMaterialIndex()
    for corpus, source, exam, text in (
        ("station", "st1", sca, "Hypertension station: safety net and review in a month."),
        ("summary", "su1", sca, "Hypertension summary: confirm with ambulatory readings."),
        ("slide_deck", "sd1", sca, "Hypertension slides."),
        ("summary", "su2", plab, "Hypertension for another exam."),
    ):
        index.passages.append(
            Passage(corpus=corpus, source_id=source, title=source, text=text, section="", score=1.0)
        )
        index.exam_of[(corpus, source)] = str(exam)
    return index


@pytest.fixture
def chat(monkeypatch):
    """Ask Athena with everything outside the slice faked; returns the prompt the model was sent."""
    sca, plab = uuid4(), uuid4()
    monkeypatch.setattr(
        service.catalog,
        "exam_refs",
        AsyncMock(return_value=[SimpleNamespace(id=sca, code="sca"), SimpleNamespace(id=plab, code="plab")]),
    )
    completion = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Grounded answer"))]
        )
    )
    open_sessions: list[int] = []

    @contextlib.asynccontextmanager
    async def opener():
        open_sessions.append(1)
        try:
            yield None
        finally:
            open_sessions.pop()

    async def only_when_no_session_is_open(**kwargs):
        assert open_sessions == [], "a database session was still open during the model call"
        return await completion_result(**kwargs)

    completion_result = completion
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=only_when_no_session_is_open))
    )
    manager = AsyncMock()
    manager.__aenter__.return_value = client
    # `answer` imports the SDK lazily inside the call, so ADR 0013 holds and
    # importing the engine pulls in no LLM SDK. Patch the source module: the
    # from-import resolves at call time, and `service` has no such attribute.
    monkeypatch.setattr(openai, "AsyncOpenAI", lambda **kwargs: manager)

    async def ask(messages, *, holds=("sca", "plab"), index="default", guidelines=None):
        held = frozenset(exam for code, exam in (("sca", sca), ("plab", plab)) if code in holds)
        monkeypatch.setattr(service.service_search, "unlocked_exam_ids", AsyncMock(return_value=held))
        completion.reset_mock()
        result = await service.answer(
            opener,
            KnowledgeChat(exam_code="sca", messages=[{"role": r, "content": c} for r, c in messages]),
            user_id=uuid4(),
            now=datetime.now(UTC),
            index=material(sca, plab) if index == "default" else index,
            guidelines=guidelines,
            settings=SimpleNamespace(openai_api_key="test", anthropic_api_key=""),
        )
        prompt = completion.call_args.kwargs["messages"][0]["content"] if completion.called else None
        return result.reply, prompt

    return ask


@pytest.mark.asyncio
async def test_an_answer_is_grounded_in_this_exams_stations_and_summaries(chat):
    reply, prompt = await chat([("user", "hypertension")])

    assert reply == "Grounded answer"
    assert "[Station: st1]\nHypertension station" in prompt
    assert "[Summary: su1]\nHypertension summary" in prompt
    assert "Hypertension slides" not in prompt
    assert "another exam" not in prompt


@pytest.mark.asyncio
async def test_guidelines_come_after_our_own_material(chat):
    guidelines = FakeGuidelineIndex([NICE])

    _reply, prompt = await chat([("user", "hypertension")], guidelines=guidelines)

    assert prompt.index("Hypertension station") < prompt.index("[NICE NG136]\nOffer an ACE inhibitor")
    assert guidelines.searches == [("hypertension", service.GUIDELINE_LIMIT, True)]


@pytest.mark.asyncio
async def test_guidelines_answer_what_our_material_does_not_hold(chat):
    reply, prompt = await chat([("user", "ace inhibitor")], guidelines=FakeGuidelineIndex([NICE]))

    assert reply == "Grounded answer"
    assert "## OSCE Guide material\n\n(nothing relevant found)" in prompt
    assert "Offer an ACE inhibitor under 55." in prompt


@pytest.mark.asyncio
async def test_a_follow_up_is_searched_with_the_question_it_follows(chat):
    guidelines = FakeGuidelineIndex([NICE])

    await chat(
        [("user", "Lyme disease"), ("assistant", "A tick-borne infection."), ("user", "drug of choice?")],
        guidelines=guidelines,
    )

    assert guidelines.searches[0][0] == "Lyme disease drug of choice?"


@pytest.mark.asyncio
async def test_nothing_found_anywhere_says_so_without_asking_the_model(chat):
    reply, prompt = await chat([("user", "gardening")], guidelines=FakeGuidelineIndex())

    assert reply.startswith("I could not find relevant passages")
    assert prompt is None


@pytest.mark.asyncio
async def test_an_exam_the_learner_does_not_hold_is_never_searched(chat):
    index, guidelines = FakeMaterialIndex(), FakeGuidelineIndex([NICE])

    reply, prompt = await chat(
        [("user", "hypertension")], holds=("plab",), index=index, guidelines=guidelines
    )

    assert reply.startswith("Your study access for this exam has expired")
    assert prompt is None
    assert index.searches == [] and guidelines.searches == []


def test_no_embedding_key_means_no_material_index():
    opener = contextlib.asynccontextmanager(lambda: (yield None))
    assert service.get_material_index(opener, SimpleNamespace(openai_api_key="")) is None
    assert isinstance(
        service.get_material_index(opener, SimpleNamespace(openai_api_key="k")), service._ShortSessionIndex
    )


@pytest.mark.asyncio
async def test_the_material_search_opens_and_closes_its_own_session(monkeypatch):
    opened: list[str] = []

    @contextlib.asynccontextmanager
    async def opener():
        opened.append("open")
        yield "session"
        opened.append("closed")

    class Inner:
        async def search(self, **kwargs):
            opened.append("search")
            return []

    monkeypatch.setattr(service.tutor_search, "material_index", lambda session: Inner())

    assert await service._ShortSessionIndex(opener).search(query="q", exam_ids=[], corpus=None, limit=1) == []
    assert opened == ["open", "search", "closed"]
