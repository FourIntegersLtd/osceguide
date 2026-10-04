"""Clinical guidelines: the second line behind our own material.

The guideline library belongs to Clinical Buddy, and so does the way it is searched: which
index and namespace, which embedding model, how keyword and meaning are fused, which
reranker. This backend knows none of that. It asks Clinical Buddy for passages over HTTP
(`POST /api/retrieve`, proved by a shared service key) and writes its own answer from them,
so a change to the search there reaches the tutor and the help chat with no change here.

A guideline is never the only thing standing between a doctor and an answer, so every
failure here is "no guidelines found", logged, and never an error the caller has to handle.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.ports import GuidelineIndex, GuidelinePassage
from app.core.settings import get_settings

log = get_logger(__name__)

RETRIEVE_PATH = "/api/retrieve"
SERVICE_KEY_HEADER = "X-Service-Key"
REQUEST_TIMEOUT_SECONDS = 10


class ClinicalBuddyGuidelines:
    """Guideline passages, as Clinical Buddy's own search finds them."""

    def __init__(self, *, http: httpx.AsyncClient, base_url: str) -> None:
        self._http = http
        self._url = base_url.rstrip("/") + RETRIEVE_PATH

    async def search(self, *, query: str, limit: int, rerank: bool) -> list[GuidelinePassage]:
        """The passages nearest `query`, best first; empty when nothing was found or it failed."""
        cleaned = " ".join(query.split())
        if not cleaned or limit <= 0:
            return []
        try:
            response = await self._http.post(
                self._url, json={"question": cleaned, "limit": limit, "rerank": rerank}
            )
            response.raise_for_status()
            found = [_passage(item) for item in response.json().get("passages") or []]
            return [passage for passage in found if passage.text][:limit]
        except Exception as exc:  # noqa: BLE001 - whatever went wrong, there are no guidelines to offer
            log.warning("guideline search failed", error=str(exc) or type(exc).__name__)
            return []


def _passage(item: dict[str, Any]) -> GuidelinePassage:
    """One guideline passage as the tutor reads it: which guideline, and what it says."""
    return GuidelinePassage(
        source=str(item.get("source") or "Clinical guideline")[:200],
        text=str(item.get("text") or "").strip(),
        score=float(item.get("score") or 0.0),
    )


@lru_cache(maxsize=1)
def _shared(base_url: str, service_key: str) -> ClinicalBuddyGuidelines:
    """One adapter for the process, so its connection to Clinical Buddy is reused.

    A new connection per question is a TLS handshake inside a voice loop.
    """
    http = httpx.AsyncClient(headers={SERVICE_KEY_HEADER: service_key}, timeout=REQUEST_TIMEOUT_SECONDS)
    return ClinicalBuddyGuidelines(http=http, base_url=base_url)


def build_guideline_index() -> GuidelineIndex | None:
    """The guideline library, or `None` where this deployment has no key for it."""
    settings = get_settings()
    base_url, service_key = settings.clinical_buddy_url.strip(), settings.clinical_buddy_service_key.strip()
    if not base_url or not service_key:
        return None
    return _shared(base_url, service_key)
