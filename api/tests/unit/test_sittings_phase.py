"""The exam clock (D-6): a phase that starts now ends when its minutes are up."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.features.sittings import domain

NOW = datetime(2026, 9, 17, 9, 0, tzinfo=UTC)


def test_reading_runs_for_the_reading_minutes() -> None:
    started, ends = domain.phase_window(
        domain.Phase.READING, reading_minutes=3, simulation_minutes=10, now=NOW
    )
    assert started == NOW
    assert ends == NOW + timedelta(minutes=3)


def test_simulation_runs_for_the_simulation_minutes() -> None:
    _, ends = domain.phase_window(domain.Phase.SIMULATION, reading_minutes=3, simulation_minutes=10, now=NOW)
    assert ends == NOW + timedelta(minutes=10)


def test_a_phase_with_no_time_is_refused() -> None:
    with pytest.raises(domain.InvalidCircuit):
        domain.phase_window(domain.Phase.READING, reading_minutes=0, simulation_minutes=10, now=NOW)
