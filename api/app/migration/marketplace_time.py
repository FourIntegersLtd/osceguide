"""Wall-clock marketplace scheduling → UTC (ported from b2c-api)."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def scheduled_local_to_utc(
    scheduled_date: str,
    scheduled_time: str,
    tz_name: str | None,
) -> datetime:
    """A marketplace slot's local wall-clock date and time, converted to UTC.

    Falls back to UTC if `tz_name` names no known zone, rather than raising: a slot
    with a slightly wrong timezone is still better recorded than dropped.
    """
    if not scheduled_date or not scheduled_time:
        raise ValueError("scheduled_date and scheduled_time are required")

    raw_tz = (tz_name or "").strip() or "UTC"
    try:
        tz = ZoneInfo(raw_tz)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")

    local_naive = datetime.strptime(f"{scheduled_date} {scheduled_time}", "%Y-%m-%d %H:%M")
    return local_naive.replace(tzinfo=tz).astimezone(UTC)
