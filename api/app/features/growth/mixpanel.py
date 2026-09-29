"""Counting partner events in Mixpanel: the adapter behind `core.ports.EventCounts`.

Over `httpx` against Mixpanel's read-only Query API, the same single request the
retiring b2c client made (`mixpanel_query_client.py`), so the counts agree with
what the old dashboard showed. Mixpanel only corroborates the arrival ledger; the
ledger in this database is what a partner is paid on.
"""

from __future__ import annotations

import json
from base64 import b64encode
from datetime import date
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.ports import EventCounts, EventCountsFailed, EventCountsUnavailable
from app.core.settings import Settings

log = get_logger(__name__)

MIXPANEL_EVENTS_URL = "https://mixpanel.com/api/2.0/events/"
TIMEOUT_SECONDS = 20.0


class MixpanelEventCounts:
    """The `EventCounts` port, answered by Mixpanel's events endpoint."""

    def __init__(self, api_secret: str) -> None:
        self._api_secret = api_secret

    async def count(self, *, event: str, from_date: date, to_date: date, where: dict[str, str]) -> int:
        """Sum one event's daily counts across the range, filtered on `where`.

        A 402 is Mixpanel saying the plan has no Query API, which is a fact
        about the account rather than a failure, so it is reported as
        unavailable.
        """
        params = {
            "event": json.dumps([event]),
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "type": "general",
        }
        if where:
            params["where"] = mixpanel_where(where)
        token = b64encode(f"{self._api_secret}:".encode()).decode()
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.get(
                    MIXPANEL_EVENTS_URL, params=params, headers={"Authorization": f"Basic {token}"}
                )
        except httpx.HTTPError as error:
            log.warning("mixpanel event count failed", mixpanel_event=event, error=str(error))
            raise EventCountsFailed(f"Mixpanel request failed: {error}") from error
        if response.status_code == 402:
            raise EventCountsUnavailable("Mixpanel Query API not available on current plan")
        if response.status_code >= 400:
            log.warning(
                "mixpanel refused an event count", status=response.status_code, body=response.text[:500]
            )
            raise EventCountsFailed(f"Mixpanel API error {response.status_code}")
        try:
            payload = response.json()
        except ValueError as error:
            raise EventCountsFailed("Mixpanel returned invalid JSON") from error
        return sum_event_counts(payload, event)


class UnavailableEventCounts:
    """What a deployment without Mixpanel gets: every count is unavailable, with the reason."""

    def __init__(self, reason: str) -> None:
        self._reason = reason

    async def count(self, *, event: str, from_date: date, to_date: date, where: dict[str, str]) -> int:
        """Always refuses with the configuration reason this was built with."""
        raise EventCountsUnavailable(self._reason)


def build_event_counts(settings: Settings) -> EventCounts:
    """The adapter this deployment's settings allow, never one that would fail on first use."""
    if not settings.mixpanel_query_api_enabled:
        return UnavailableEventCounts("Mixpanel Query API is disabled; the ledger is the source of truth")
    if not settings.mixpanel_api_secret:
        return UnavailableEventCounts("Mixpanel API secret not configured (MIXPANEL_API_SECRET)")
    return MixpanelEventCounts(settings.mixpanel_api_secret)


def mixpanel_where(where: dict[str, str]) -> str:
    """Mixpanel's filter expression: every property equal to its value, joined by `and`."""
    return " and ".join(
        f"properties[{json.dumps(name)}] == {json.dumps(value)}" for name, value in where.items()
    )


def sum_event_counts(payload: Any, event: str) -> int:
    """One event's total out of Mixpanel's `{data: {values: {event: {day: count}}}}`.

    Anything shaped otherwise counts as zero, as it did in b2c.
    """
    body = payload.get("data") if isinstance(payload, dict) else None
    values = body.get("values") if isinstance(body, dict) else None
    per_day = values.get(event) if isinstance(values, dict) else None
    if isinstance(per_day, (int, float)):
        return int(per_day)
    if not isinstance(per_day, dict):
        return 0
    return sum(int(count) for count in per_day.values() if isinstance(count, (int, float)))
