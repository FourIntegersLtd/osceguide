"""Clinical guidelines: the second line behind our own material.

The guideline library belongs to Clinical Buddy, and so does the way it is searched: which
index and namespace, which embedding model, how keyword and meaning are fused, which
reranker. This backend knows none of that. It asks Clinical Buddy for passages over HTTP
(`POST /api/retrieve`, proved by a shared service key) and writes its own answer from them,
so a change to the search there reaches the tutor and the help chat with no change here.
The same goes for the clinical web: `POST /api/web-search` runs Clinical Buddy's own web search
and hands back its answer with the pages it cites, for checking what we are about to publish.

A guideline is never the only thing standing between a doctor and an answer, so every
failure here is "no guidelines found", logged, and never an error the caller has to handle.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.ports import GuidelineIndex, GuidelinePassage, GuidelineWeb, WebAnswer
from app.core.settings import get_settings

log = get_logger(__name__)

RETRIEVE_PATH = "/api/retrieve"
SERVICE_KEY_HEADER = "X-Service-Key"
REQUEST_TIMEOUT_SECONDS = 10
WEB_SEARCH_PATH = "/api/web-search"
# A web answer is several searches and model calls on Clinical Buddy's side.
WEB_SEARCH_TIMEOUT_SECONDS = 90
# Questions of each kind in flight from this process, whoever asks. Three fact checks at once sent
# about 72 web searches: 46 came back 502 and 77 library searches timed out, each one read as
# "nothing found". 24 at once it has answered with none refused.
AT_ONCE = 24


class ClinicalBuddyGuidelines:
    """Guideline passages, as Clinical Buddy's own search finds them."""

    def __init__(self, *, http: httpx.AsyncClient, base_url: str) -> None:
        self._http = http
        self._url = base_url.rstrip("/") + RETRIEVE_PATH
        self._web_url = base_url.rstrip("/") + WEB_SEARCH_PATH
        self._searching = asyncio.Semaphore(AT_ONCE)
        self._answering = asyncio.Semaphore(AT_ONCE)

    async def search(self, *, query: str, limit: int, rerank: bool) -> list[GuidelinePassage]:
        """The passages nearest `query`, best first; empty when nothing was found or it failed."""
        cleaned = " ".join(query.split())
        if not cleaned or limit <= 0:
            return []
        try:
            async with self._searching:
                response = await self._http.post(
                    self._url, json={"question": cleaned, "limit": limit, "rerank": rerank}
                )
            response.raise_for_status()
            found = [_passage(item) for item in response.json().get("passages") or []]
            return [passage for passage in found if passage.text][:limit]
        except Exception as exc:  # noqa: BLE001 - whatever went wrong, there are no guidelines to offer
            log.warning("guideline search failed", error=str(exc) or type(exc).__name__)
            return []

    async def answer(self, *, question: str) -> WebAnswer | None:
        """The clinical web's answer to `question`; `None` when it failed or had nothing to stand on."""
        cleaned = " ".join(question.split())
        if not cleaned:
            return None
        try:
            async with self._answering:
                response = await self._web_answer(cleaned)
                if response.status_code >= 500:
                    # Overloaded or restarting: worth one more ask before "nothing found".
                    response = await self._web_answer(cleaned)
            response.raise_for_status()
            body = response.json()
            text = str(body.get("answer") or "").strip()
            if body.get("status") != 200 or not text:
                return None
            return WebAnswer(
                answer=text,
                references=[item for item in body.get("references") or [] if isinstance(item, dict)],
                gaps=[str(item) for item in body.get("evidence_gaps") or []],
                flagged=[str(item) for item in body.get("flagged_claims") or []],
            )
        except Exception as exc:  # noqa: BLE001 - whatever went wrong, the web has nothing to offer
            log.warning("guideline web search failed", error=str(exc) or type(exc).__name__)
            return None

    async def _web_answer(self, question: str) -> httpx.Response:
        """One ask of the clinical web."""
        return await self._http.post(
            self._web_url, json={"question": question}, timeout=WEB_SEARCH_TIMEOUT_SECONDS
        )


def _passage(item: dict[str, Any]) -> GuidelinePassage:
    """One guideline passage as the tutor reads it: which guideline, and what it says."""
    return GuidelinePassage(
        source=str(item.get("source") or "Clinical guideline")[:200],
        text=str(item.get("text") or "").strip(),
        score=float(item.get("score") or 0.0),
        section=str(item.get("section") or "")[:200],
        page=item["page"] if isinstance(item.get("page"), int) else None,
        reliability=str(item.get("reliability") or "")[:40],
        source_type=str(item.get("source_type") or "")[:80],
    )


@lru_cache(maxsize=1)
def _shared(base_url: str, service_key: str) -> ClinicalBuddyGuidelines:
    """One adapter for the process, so its connection to Clinical Buddy is reused.

    A new connection per question is a TLS handshake inside a voice loop.
    """
    http = httpx.AsyncClient(headers={SERVICE_KEY_HEADER: service_key}, timeout=REQUEST_TIMEOUT_SECONDS)
    return ClinicalBuddyGuidelines(http=http, base_url=base_url)


def _clinical_buddy() -> ClinicalBuddyGuidelines | None:
    """The adapter for this deployment, or `None` where it has no key for Clinical Buddy."""
    settings = get_settings()
    base_url, service_key = settings.clinical_buddy_url.strip(), settings.clinical_buddy_service_key.strip()
    if not base_url or not service_key:
        return None
    return _shared(base_url, service_key)


def build_guideline_index() -> GuidelineIndex | None:
    """The guideline library, or `None` where this deployment has no key for it."""
    return _clinical_buddy()


def build_guideline_web() -> GuidelineWeb | None:
    """The clinical web search, or `None` where this deployment has no key for it."""
    return _clinical_buddy()
