"""When the database reaches its budget: the thresholds and the forecast, as pure arithmetic."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from math import ceil
from typing import Literal

MIB = 1024 * 1024

# Fractions of the budget at which something is raised: an audit row, then a page to a person.
WARNING_AT = 0.60
CRITICAL_AT = 0.80

# A trend needs both: enough readings, and enough days between the first and last for the slope to
# mean something. Two readings a week apart, or eight in a morning, extrapolate noise.
MIN_READINGS = 7
MIN_SPAN_DAYS = 14
# The fit looks at the last two months, so an old growth rate does not outvote this one.
WINDOW_DAYS = 60
# A fall of this much between neighbouring readings is a cleanup (a reindex, a compaction), not a
# trend: the fit restarts after it, or the step would read as a database that is shrinking.
CLEANUP_DROP = 0.05

ForecastState = Literal["insufficient_data", "not_growing", "growing", "over_budget"]


@dataclass(frozen=True)
class Forecast:
    """Where the database is heading: the state, the daily growth and the days left when growing."""

    state: ForecastState
    bytes_per_day: int | None
    days_until_full: int | None
    readings_used: int


def alert_level(total_bytes: int, budget_bytes: int) -> int:
    """0 below the warning threshold, 1 from 60% of the budget, 2 from 80%."""
    if total_bytes >= budget_bytes * CRITICAL_AT:
        return 2
    if total_bytes >= budget_bytes * WARNING_AT:
        return 1
    return 0


def _since_last_cleanup(readings: Sequence[tuple[date, int]]) -> list[tuple[date, int]]:
    """The readings after the newest sharp fall, oldest first (all of them if there was none)."""
    start = 0
    for index in range(1, len(readings)):
        if readings[index][1] < readings[index - 1][1] * (1 - CLEANUP_DROP):
            start = index
    return list(readings[start:])


def _slope_per_day(readings: Sequence[tuple[date, int]]) -> float:
    """Least-squares growth in bytes a day: one wobbly reading cannot swing it as it can two endpoints."""
    first = readings[0][0]
    day_numbers = [(day - first).days for day, _ in readings]
    totals = [total for _, total in readings]
    mean_day = sum(day_numbers) / len(day_numbers)
    mean_total = sum(totals) / len(totals)
    spread = sum((number - mean_day) ** 2 for number in day_numbers)
    covariance = sum(
        (number - mean_day) * (total - mean_total) for number, total in zip(day_numbers, totals, strict=True)
    )
    return covariance / spread


def forecast(readings: Sequence[tuple[date, int]], budget_bytes: int) -> Forecast:
    """The trend of `(day, total bytes)` readings, oldest first, against the budget.

    Says `insufficient_data` rather than extrapolate from too little.
    """
    if not readings:
        return Forecast("insufficient_data", None, None, 0)
    newest = readings[-1][0]
    recent = [(day, total) for day, total in readings if (newest - day).days <= WINDOW_DAYS]
    used = _since_last_cleanup(recent)
    if len(used) < MIN_READINGS or (used[-1][0] - used[0][0]).days < MIN_SPAN_DAYS:
        return Forecast("insufficient_data", None, None, len(used))
    latest = used[-1][1]
    if latest >= budget_bytes:
        return Forecast("over_budget", None, 0, len(used))
    slope = _slope_per_day(used)
    if slope <= 0:
        return Forecast("not_growing", None, None, len(used))
    return Forecast("growing", round(slope), ceil((budget_bytes - latest) / slope), len(used))


def _mib(size: float) -> str:
    return f"{size / MIB:.1f}".removesuffix(".0")


def describe(result: Forecast) -> str:
    """One sentence for the Ops screen and the alarm."""
    if result.state == "insufficient_data":
        return (
            f"There is not enough history to forecast yet ({result.readings_used} readings; "
            f"a trend needs {MIN_READINGS} across at least {MIN_SPAN_DAYS} days)."
        )
    if result.state == "over_budget":
        return "The database is at or over its budget."
    if result.state == "not_growing" or result.bytes_per_day is None or result.days_until_full is None:
        return "The database is not growing."
    rate = f"At the current rate of {_mib(result.bytes_per_day)} MB a day"
    if result.days_until_full < 14:
        return f"{rate} it reaches the budget in about {result.days_until_full} days."
    return f"{rate} it reaches the budget in about {round(result.days_until_full / 7)} weeks."
