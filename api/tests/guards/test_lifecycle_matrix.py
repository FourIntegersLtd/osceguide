"""The lifecycle matrix: one expected answer for every state x operation it applies to.

Each state an organisation, a membership, a trainee, a programme or exam, a
station, an entitlement or an account can reach is applied to a real world (an
org, a sitting, a circuit, a rostered candidate, a plan), then each operation it
touches runs through its real HTTP route and must give exactly one answer:
a status and an error code, or a status and what the caller can see.

Sibling gates used to disagree here (a suspended org's console stream closed
while the circuit it watches was allowed to run). A cell that disagrees with
its row is a bug in a gate, not in the table. test_lifecycle_states_have_rows keeps
the table complete: every status literal the lifecycle models use is a state
here or on its allow-list with a reason.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.lifecycle_world import OPERATIONS, STATES, Answer, World, build_world

SUSPENDED = "organization_suspended"
CLOSED = (401, "account_suspended")


def _org_stopped() -> dict[str, Answer]:
    """S-17 / S-29 / S-15: a running circuit finishes, staff can watch it, nothing new starts."""
    return {
        "start": (403, SUSPENDED),
        "join": (200, "ok"),
        "mark": (403, SUSPENDED),
        "release": (403, SUSPENDED),
        "my_sittings": (200, "listed"),
        "my_result": (200, "shown"),
        "console": (200, "ok"),
        "console_stream": (200, "open"),
        "sit": (403, "not_entitled"),
    }


def _lapsed() -> dict[str, Answer]:
    """S-11: a lapse ends new and resumed attempts, never the one running; buying again is the way back."""
    return {
        "sit": (403, "not_entitled"),
        "attempt_stream": (200, "open"),
        "checkout": (201, "ok"),
        "my_entitlements": (200, "not_live"),
    }


def _account_gone() -> dict[str, Answer]:
    """A closed or deactivated account is refused everywhere, streams included."""
    return {
        op: CLOSED
        for op in (
            "join",
            "my_sittings",
            "my_sittings_stream",
            "my_result",
            "sit",
            "attempt_stream",
            "checkout",
            "my_entitlements",
        )
    }


MATRIX: dict[str, dict[str, Answer]] = {
    "baseline": {
        "start": (200, "ok"),
        "join": (200, "ok"),
        "mark": (200, "ok"),
        "release": (200, "ok"),
        "my_sittings": (200, "listed"),
        "my_sittings_stream": (200, "listed"),
        "my_result": (200, "shown"),
        "console": (200, "ok"),
        "console_stream": (200, "open"),
        "live_stream": (200, "open"),
        "my_transcript": (200, "ok"),
        "my_marks": (200, "ok"),
        "sit": (201, "ok"),
        "attempt_stream": (200, "open"),
        "checkout": (201, "ok"),
        "my_entitlements": (200, "live"),
    },
    "org_suspended": _org_stopped(),
    "contract_ended": _org_stopped(),
    "membership_removed": {
        "start": (403, "forbidden"),
        "mark": (403, "forbidden"),
        "release": (403, "forbidden"),
        "console": (403, "forbidden"),
        "console_stream": (403, "forbidden"),
        "live_stream": (403, "forbidden"),
    },
    # T-13: a revoked trainee sees nothing from that org, and cannot get into its rooms.
    # The institution still marks and releases: the record is theirs, not the trainee's.
    "trainee_revoked": {
        "join": (409, "trainee_revoked"),
        "my_sittings": (200, "hidden"),
        "my_sittings_stream": (200, "hidden"),
        "my_result": (200, "hidden"),
        "my_transcript": (404, "result_not_released"),
        "my_marks": (404, "result_not_released"),
        "mark": (200, "ok"),
        "release": (200, "ok"),
    },
    # S-28 / S-24: a retired programme keeps its sittings and blocks new starts.
    "programme_retired": {
        "start": (409, "programme_not_active"),
        "join": (200, "ok"),
        "mark": (200, "ok"),
        "release": (200, "ok"),
        "my_sittings": (200, "listed"),
        "my_result": (200, "shown"),
    },
    "exam_retired": {
        "start": (409, "programme_not_active"),
        "join": (200, "ok"),
        "sit": (404, "unknown_exam"),
        "checkout": (404, "plan_not_available"),
    },
    "station_archived": {"sit": (409, "station_not_published")},
    "entitlement_lapsed": _lapsed(),
    "entitlement_refunded": _lapsed(),
    "account_closed": _account_gone(),
    "account_deactivated": _account_gone(),
}

CELLS = [
    pytest.param(state, op, expected, id=f"{state}-{op}")
    for state, row in MATRIX.items()
    for op, expected in row.items()
]


@pytest.fixture
async def world(
    client: AsyncClient,
    streaming_client: AsyncClient,
    make_actor: Callable[..., Awaitable[str]],
    db_session: AsyncSession,
) -> World:
    return await build_world(client, streaming_client, make_actor, db_session)


@pytest.mark.db
@pytest.mark.parametrize(("state", "op", "expected"), CELLS)
async def test_each_state_gives_each_operation_one_answer(
    world: World, state: str, op: str, expected: Answer
) -> None:
    prepare, act = OPERATIONS[op]
    await prepare(world)
    await STATES[state](world)
    assert await act(world) == expected


def test_every_state_has_a_row_and_every_cell_an_operation() -> None:
    assert set(MATRIX) == set(STATES)
    assert {op for row in MATRIX.values() for op in row} <= set(OPERATIONS)
