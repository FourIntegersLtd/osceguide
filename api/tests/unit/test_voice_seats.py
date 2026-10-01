"""Seats on Cloud and our own workers, and the line for when both are full.

Run against a real Redis (the `seat_redis` fixture): admission is one Lua
script so that API replicas cannot hand out the same last seat, and it is the
script's behaviour these tests pin, not a Python copy of it.
"""

from __future__ import annotations

import pytest

from app.core.settings import Settings
from app.features.voice import capacity, seats
from app.features.voice.seats import Admission, Placement, Standing


def small_settings(**overrides: object) -> Settings:
    """One Cloud seat and one of ours, so a third candidate already waits."""
    values: dict[str, object] = {"livekit_cloud_max_concurrent": 1, "livekit_self_hosted_seats": 1}
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


@pytest.mark.usefixtures("seat_redis")
async def test_cloud_fills_first_then_our_workers_then_the_line() -> None:
    settings = small_settings()

    assert await seats.admit(settings, "room_a", use_cloud=True) == Admission(Placement.CLOUD, 0)
    assert await seats.admit(settings, "room_b", use_cloud=True) == Admission(Placement.SELF_HOSTED, 0)
    assert await seats.admit(settings, "room_c", use_cloud=True) == Admission(Placement.QUEUED, 1)
    assert await seats.admit(settings, "room_d", use_cloud=True) == Admission(Placement.QUEUED, 2)


@pytest.mark.usefixtures("seat_redis")
async def test_asking_again_keeps_your_seat_or_your_place() -> None:
    """A reload must not take a second seat, or send a waiter to the back."""
    settings = small_settings()
    await seats.admit(settings, "room_a", use_cloud=True)
    await seats.admit(settings, "room_b", use_cloud=True)
    await seats.admit(settings, "room_c", use_cloud=True)
    await seats.admit(settings, "room_d", use_cloud=True)

    assert await seats.admit(settings, "room_a", use_cloud=True) == Admission(Placement.CLOUD, 0)
    assert await seats.admit(settings, "room_b", use_cloud=True) == Admission(Placement.SELF_HOSTED, 0)
    assert await seats.admit(settings, "room_c", use_cloud=True) == Admission(Placement.QUEUED, 1)


@pytest.mark.usefixtures("seat_redis")
async def test_a_freed_seat_is_held_for_the_front_of_the_line_not_a_newcomer() -> None:
    settings = small_settings()
    for room in ("room_a", "room_b", "room_c", "room_d"):
        await seats.admit(settings, room, use_cloud=True)

    assert await seats.release("room_b") is True

    assert await seats.standing(settings, "room_c", use_cloud=True) == Standing(ready=True, position=1)
    assert await seats.standing(settings, "room_d", use_cloud=True) == Standing(ready=False, position=2)
    assert await seats.admit(settings, "room_e", use_cloud=True) == Admission(Placement.QUEUED, 3)
    assert await seats.admit(settings, "room_c", use_cloud=True) == Admission(Placement.SELF_HOSTED, 0)
    assert await seats.standing(settings, "room_d", use_cloud=True) == Standing(ready=False, position=1)


@pytest.mark.usefixtures("seat_redis")
async def test_without_cloud_only_our_own_seats_count() -> None:
    settings = small_settings()

    assert await seats.admit(settings, "room_a", use_cloud=False) == Admission(Placement.SELF_HOSTED, 0)
    assert await seats.admit(settings, "room_b", use_cloud=False) == Admission(Placement.QUEUED, 1)


@pytest.mark.usefixtures("seat_redis")
async def test_a_waiter_who_stops_watching_loses_their_place() -> None:
    """A closed tab must not hold up everyone behind it forever."""
    settings = small_settings()
    for room in ("room_a", "room_b"):
        await seats.admit(settings, room, use_cloud=True)
    # Nobody refreshes room_c's place, so it lapses at once.
    await seats.admit(small_settings(livekit_queue_waiter_ttl_seconds=0), "room_c", use_cloud=True)
    await seats.admit(settings, "room_d", use_cloud=True)

    assert await seats.standing(settings, "room_d", use_cloud=True) == Standing(ready=False, position=1)
    assert await seats.standing(settings, "room_c", use_cloud=True) == Standing(ready=True, position=0)


@pytest.mark.usefixtures("seat_redis")
async def test_a_circuit_holds_a_seat_and_only_held_seats_are_extended() -> None:
    settings = small_settings()
    await seats.hold(settings, "circuit_room")

    assert await seats.admit(settings, "room_a", use_cloud=False) == Admission(Placement.QUEUED, 1)
    assert await seats.extend(settings, "never_seated") is False
    assert await seats.extend(settings, "circuit_room") is True
    assert await seats.release("circuit_room") is True
    assert await seats.standing(settings, "room_a", use_cloud=False) == Standing(ready=True, position=1)


async def test_without_redis_candidates_are_served_by_our_workers(monkeypatch: pytest.MonkeyPatch) -> None:
    """A cache outage must not turn every candidate away, as the Cloud counter never has."""
    monkeypatch.setattr(capacity, "get_redis", lambda: None)
    settings = small_settings()

    assert await seats.admit(settings, "room_a", use_cloud=True) == Admission(Placement.SELF_HOSTED, 0)
    assert await seats.standing(settings, "room_a", use_cloud=True) == Standing(ready=True, position=0)
