"""The one-off transcript backfill: what an operator is told, and what it leaves in the database."""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.models import Transcript
from tests.support.transcripts import add_turns, an_attempt, row_count

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "compact_transcripts.py"
URL = "postgresql://u:secret@localhost:5432/osce_test"


@pytest.fixture(scope="module")
def script() -> Iterator[ModuleType]:
    """The script loaded once; its import-time `sys.path` and `APP_ENV` edits are undone after."""
    patch = pytest.MonkeyPatch()
    patch.setattr(sys, "path", list(sys.path))
    patch.setenv("APP_ENV", "test")
    spec = importlib.util.spec_from_file_location("compact_transcripts_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    yield module
    patch.undo()


class _Engine:
    async def dispose(self) -> None: ...


@pytest.fixture
def vacuums() -> list[bool]:
    return []


@pytest.fixture
def operator(
    script: ModuleType, db_session: AsyncSession, vacuums: list[bool], monkeypatch: pytest.MonkeyPatch
) -> ModuleType:
    """The script pointed at the test transaction: every session it opens is a savepoint of it."""
    factory = async_sessionmaker(
        bind=db_session.bind, join_transaction_mode="create_savepoint", expire_on_commit=False
    )

    async def fake_vacuum(url: str, _factory: object, *, full: bool) -> None:
        vacuums.append(full)

    monkeypatch.setattr(script, "create_async_engine", lambda *_a, **_k: _Engine())
    monkeypatch.setattr(script, "async_sessionmaker", lambda *_a, **_k: factory)
    monkeypatch.setattr(script, "vacuum", fake_vacuum)
    return script


def _args(*, yes: bool, vacuum: bool = True) -> argparse.Namespace:
    return argparse.Namespace(yes=yes, vacuum=vacuum, full=False, batch_size=200)


async def _delivered(session: AsyncSession, minutes_ago: int, turns: int = 3) -> uuid.UUID:
    attempt_id = await an_attempt(session)
    await add_turns(session, attempt_id, turns)
    at = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    await transcripts.mark_transcript_complete(session, attempt_id, runtime_label=None, at=at)
    return attempt_id


async def _compacted(session: AsyncSession, ids: list[uuid.UUID]) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(Transcript)
            .where(Transcript.attempt_id.in_(ids), Transcript.message_count.is_not(None))
        )
        or 0
    )


def _reported_total(out: str) -> int:
    match = re.search(r"Compacted ([\d,]+) attempts this run", out)
    assert match, out
    return int(match.group(1).replace(",", ""))


async def test_a_dry_run_writes_nothing(
    operator: ModuleType, db_session: AsyncSession, vacuums: list[bool], capsys: pytest.CaptureFixture[str]
) -> None:
    ids = [await _delivered(db_session, 120), await _delivered(db_session, 121)]

    assert await operator.main(_args(yes=False), URL) == 0

    assert await _compacted(db_session, ids) == 0
    assert [await row_count(db_session, i) for i in ids] == [3, 3]
    assert vacuums == []
    assert "Dry run, nothing written" in capsys.readouterr().out


async def test_a_failed_attempt_stops_the_run_before_vacuum_and_the_count_is_exact(
    operator: ModuleType,
    db_session: AsyncSession,
    vacuums: list[bool],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    good = [await _delivered(db_session, 120), await _delivered(db_session, 121)]
    poisoned = await _delivered(db_session, 10_000)
    real_compact = transcripts.compact

    async def compact(session: AsyncSession, attempt_id: uuid.UUID) -> bool:
        if attempt_id == poisoned:
            raise RuntimeError("poisoned")
        return await real_compact(session, attempt_id)

    monkeypatch.setattr(transcripts, "compact", compact)

    assert await operator.main(_args(yes=True), URL) == 1

    captured = capsys.readouterr()
    assert vacuums == []
    assert await _compacted(db_session, [*good, poisoned]) == 2
    assert _reported_total(captured.out) == 2
    assert str(poisoned) in captured.err
    assert await row_count(db_session, poisoned) == 3


async def test_attempts_that_become_ready_mid_run_are_compacted_and_counted(
    operator: ModuleType,
    db_session: AsyncSession,
    vacuums: list[bool],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = await _delivered(db_session, 120)
    late = [await _delivered(db_session, 30), await _delivered(db_session, 31)]  # inside the grace hour
    real_compact = transcripts.compact

    async def compact(session: AsyncSession, attempt_id: uuid.UUID) -> bool:
        done = await real_compact(session, attempt_id)
        if attempt_id == first:  # the clock passes the grace hour while the batch runs
            await session.execute(
                update(Transcript)
                .where(Transcript.attempt_id.in_(late))
                .values(delivered_at=datetime.now(UTC) - timedelta(hours=3))
            )
        return done

    monkeypatch.setattr(transcripts, "compact", compact)

    assert await operator.main(_args(yes=True), URL) == 0

    captured = capsys.readouterr()
    assert "No progress" not in captured.err
    assert await _compacted(db_session, [first, *late]) == 3
    assert _reported_total(captured.out) == 3
    assert vacuums == [False]


async def test_a_read_only_database_gets_the_hint_not_a_list_of_failed_attempts(
    operator: ModuleType, db_session: AsyncSession, vacuums: list[bool], capsys: pytest.CaptureFixture[str]
) -> None:
    ids = [await _delivered(db_session, 120), await _delivered(db_session, 121)]
    await db_session.execute(text("set transaction_read_only = on"))  # what an over-quota host does

    assert await operator.main(_args(yes=True), URL) == 1

    err = capsys.readouterr().err
    assert "read-only" in err and "default_transaction_read_only" in err
    assert "FAILED" not in err and str(ids[0]) not in err
    assert vacuums == []


def test_vacuum_is_refused_on_the_transaction_pooler_and_names_the_port_to_use(script: ModuleType) -> None:
    url = "postgresql://postgres.abc:secret@aws-0-eu-west-2.pooler.supabase.com:6543/postgres"
    reason = script.vacuum_refusal(url)
    assert reason is not None and "port 5432" in reason and "6543" in reason
    assert "secret" not in reason


def test_vacuum_is_allowed_on_the_session_pooler_and_a_direct_connection(script: ModuleType) -> None:
    assert script.vacuum_refusal("postgresql://u:p@aws-0-eu-west-2.pooler.supabase.com:5432/postgres") is None
    assert script.vacuum_refusal("postgresql://u:p@localhost/osce_platform") is None


def test_the_target_line_never_carries_credentials(script: ModuleType) -> None:
    assert (
        script.describe("postgresql://u:hunter2@db.example.com:5432/postgres")
        == "db.example.com:5432/postgres"
    )
