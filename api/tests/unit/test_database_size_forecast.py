"""When will the database reach its budget: the arithmetic behind the Ops screen's forecast.

The 500 MB cliff on the free plan is why this exists. A forecast from too little data is worse than
none, so the first cases are about what it refuses to say.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.features.health import domain

MB = 1024 * 1024
BUDGET = 500 * MB
START = date(2026, 10, 1)


def series(*megabytes: float, every_days: int = 1) -> list[tuple[date, int]]:
    return [(START + timedelta(days=i * every_days), int(mb * MB)) for i, mb in enumerate(megabytes)]


def test_two_readings_a_week_apart_are_not_a_trend() -> None:
    result = domain.forecast(series(100, 130, every_days=7), BUDGET)
    assert result.state == "insufficient_data"
    assert result.days_until_full is None
    assert result.bytes_per_day is None
    assert result.readings_used == 2


def test_many_readings_inside_a_few_days_are_not_a_trend_either() -> None:
    result = domain.forecast(series(100, 101, 102, 103, 104, 105, 106, 107), BUDGET)
    assert result.state == "insufficient_data"


def test_a_steady_climb_says_how_many_days_are_left() -> None:
    # 2 MB a day for 20 days: 100 -> 138 MB; 362 MB to go at 2 MB a day is 181 days.
    result = domain.forecast(series(*[100 + 2 * i for i in range(20)]), BUDGET)
    assert result.state == "growing"
    assert result.bytes_per_day == 2 * MB
    assert result.days_until_full == 181


def test_a_flat_database_is_not_growing() -> None:
    result = domain.forecast(series(*[200] * 20), BUDGET)
    assert result.state == "not_growing"
    assert result.days_until_full is None


def test_a_database_at_the_budget_is_over_it_whatever_the_slope() -> None:
    result = domain.forecast(series(*[500 + i for i in range(20)]), BUDGET)
    assert result.state == "over_budget"
    assert result.days_until_full == 0


def test_a_drop_after_a_cleanup_does_not_make_the_database_look_shrinking() -> None:
    # 546 MB, a rebuild takes it to 190, then 1 MB a day. The fall is a step, not the trend.
    before = [540 + i for i in range(10)]
    after = [190 + i for i in range(15)]
    result = domain.forecast(series(*before, *after), BUDGET)
    assert result.state == "growing"
    assert result.bytes_per_day == MB
    assert result.readings_used == 15


def test_a_cleanup_with_too_few_readings_since_says_so() -> None:
    result = domain.forecast(series(*[540 + i for i in range(10)], 190, 191, 192), BUDGET)
    assert result.state == "insufficient_data"
    assert result.readings_used == 3


def test_a_noisy_week_does_not_swing_the_slope() -> None:
    # +-1 MB wobble around 1 MB a day: the fitted line, not the last two points, decides.
    wobble = [100 + i + (1 if i % 2 else -1) for i in range(20)]
    result = domain.forecast(series(*wobble), BUDGET)
    assert result.state == "growing"
    assert abs(result.bytes_per_day - MB) < 0.1 * MB


def test_alert_levels_follow_the_two_thresholds() -> None:
    assert domain.alert_level(299 * MB, BUDGET) == 0
    assert domain.alert_level(300 * MB, BUDGET) == 1
    assert domain.alert_level(399 * MB, BUDGET) == 1
    assert domain.alert_level(400 * MB, BUDGET) == 2
    assert domain.alert_level(900 * MB, BUDGET) == 2


def test_the_sentence_names_the_weeks_left() -> None:
    result = domain.forecast(series(*[100 + 2 * i for i in range(20)]), BUDGET)
    assert (
        domain.describe(result)
        == "At the current rate of 2 MB a day it reaches the budget in about 26 weeks."
    )
    assert "not enough history" in domain.describe(domain.forecast(series(100, 101), BUDGET))


def test_the_forecast_states_the_api_speaks_are_the_ones_the_arithmetic_returns() -> None:
    """The schema may not import the domain, so its list of states is pinned to the domain's here."""
    from typing import get_args

    from app.features.health import domain
    from app.features.health.schemas import SizeForecastRead

    assert get_args(SizeForecastRead.model_fields["state"].annotation) == get_args(domain.ForecastState)
