"""The Clinical Buddy adapter against a scripted Clinical Buddy: what it asks, what it makes of the reply."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.features.tutor_memory.guidelines import ClinicalBuddyGuidelines

REPLY = {
    "reranked": True,
    "passages": [
        {
            "id": "a:chunk_0",
            "source": "NICE NG136",
            "section": "Step 1",
            "page": 4,
            "text": "ACE inhibitor.",
            "score": 0.9,
        },
        {"id": "b:chunk_3", "source": "", "text": "Colchicine.", "score": 0.8},
        {"id": "c:chunk_1", "source": "Empty", "text": "  ", "score": 0.7},
    ],
}


def guidelines_over(handler) -> tuple[ClinicalBuddyGuidelines, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    http = httpx.AsyncClient(transport=httpx.MockTransport(record), headers={"X-Service-Key": "s3cret"})
    return ClinicalBuddyGuidelines(http=http, base_url="https://buddy.test/"), seen


@pytest.mark.asyncio
async def test_a_search_is_one_keyed_request_and_skips_passages_with_no_text() -> None:
    guidelines, seen = guidelines_over(lambda request: httpx.Response(200, json=REPLY))

    found = await guidelines.search(query="  gout   treatment ", limit=5, rerank=True)

    assert [(p.source, p.text, p.score) for p in found] == [
        ("NICE NG136", "ACE inhibitor.", 0.9),
        ("Clinical guideline", "Colchicine.", 0.8),
    ]
    assert [str(request.url) for request in seen] == ["https://buddy.test/api/retrieve"]
    assert seen[0].headers["X-Service-Key"] == "s3cret"
    assert json.loads(seen[0].content) == {"question": "gout treatment", "limit": 5, "rerank": True}


@pytest.mark.asyncio
async def test_no_more_than_the_limit_is_kept() -> None:
    guidelines, _seen = guidelines_over(lambda request: httpx.Response(200, json=REPLY))

    assert [p.source for p in await guidelines.search(query="gout", limit=1, rerank=False)] == ["NICE NG136"]


@pytest.mark.asyncio
async def test_an_empty_question_asks_nothing() -> None:
    guidelines, seen = guidelines_over(lambda request: httpx.Response(200, json=REPLY))

    assert await guidelines.search(query="   ", limit=5, rerank=False) == []
    assert seen == []


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 500, 503])
async def test_clinical_buddy_refusing_or_down_is_no_guidelines_rather_than_an_error(status: int) -> None:
    guidelines, _seen = guidelines_over(lambda request: httpx.Response(status))

    assert await guidelines.search(query="gout", limit=5, rerank=False) == []


@pytest.mark.asyncio
async def test_a_dropped_connection_is_no_guidelines_rather_than_an_error() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unreachable")

    guidelines, _seen = guidelines_over(refuse)

    assert await guidelines.search(query="gout", limit=5, rerank=False) == []


@pytest.mark.asyncio
async def test_a_passage_carries_the_section_and_page_it_is_cited_by() -> None:
    guidelines, _seen = guidelines_over(lambda request: httpx.Response(200, json=REPLY))

    found = await guidelines.search(query="gout", limit=5, rerank=False)

    assert [(p.section, p.page) for p in found] == [("Step 1", 4), ("", None)]


WEB_REPLY = {
    "status": 200,
    "answer": "Stage 2 is 160/100 or more [1].",
    "references": [
        {"title": "NICE NG136", "url": "https://www.nice.org.uk/guidance/ng136", "quotes": ["160/100"]}
    ],
    "evidence_gaps": ["No trial data"],
    "flagged_claims": [],
}


@pytest.mark.asyncio
async def test_a_web_answer_is_one_keyed_request_and_keeps_its_references() -> None:
    guidelines, seen = guidelines_over(lambda request: httpx.Response(200, json=WEB_REPLY))

    found = await guidelines.answer(question="  stage 2   threshold ")

    assert found is not None
    assert found.answer == "Stage 2 is 160/100 or more [1]."
    assert [reference["url"] for reference in found.references] == ["https://www.nice.org.uk/guidance/ng136"]
    assert list(found.gaps) == ["No trial data"]
    assert [str(request.url) for request in seen] == ["https://buddy.test/api/web-search"]
    assert seen[0].headers["X-Service-Key"] == "s3cret"
    assert json.loads(seen[0].content) == {"question": "stage 2 threshold"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reply",
    [httpx.Response(401), httpx.Response(503), httpx.Response(200, json={"status": 500, "answer": "x"})],
)
async def test_a_web_search_that_fails_is_no_answer_rather_than_an_error(reply: httpx.Response) -> None:
    guidelines, _seen = guidelines_over(lambda request: reply)

    assert await guidelines.answer(question="stage 2 threshold") is None


@pytest.mark.asyncio
async def test_a_web_search_met_by_an_overloaded_clinical_buddy_is_asked_once_more() -> None:
    replies = iter([httpx.Response(502), httpx.Response(200, json=WEB_REPLY)])
    guidelines, seen = guidelines_over(lambda request: next(replies))

    found = await guidelines.answer(question="stage 2 threshold")

    assert found is not None and found.answer == "Stage 2 is 160/100 or more [1]."
    assert len(seen) == 2


@pytest.mark.asyncio
async def test_only_so_many_web_searches_are_in_flight_at_once_whoever_asks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.features.tutor_memory.guidelines.AT_ONCE", 2)
    flying: list[int] = []
    now = 0

    async def slow(request: httpx.Request) -> httpx.Response:
        nonlocal now
        now += 1
        flying.append(now)
        await asyncio.sleep(0.01)
        now -= 1
        return httpx.Response(200, json=WEB_REPLY)

    http = httpx.AsyncClient(transport=httpx.MockTransport(slow))
    guidelines = ClinicalBuddyGuidelines(http=http, base_url="https://buddy.test/")

    await asyncio.gather(*(guidelines.answer(question=f"question {number}") for number in range(6)))

    assert max(flying) == 2
