"""The Clinical Buddy adapter against a scripted Clinical Buddy: what it asks, what it makes of the reply."""

from __future__ import annotations

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
