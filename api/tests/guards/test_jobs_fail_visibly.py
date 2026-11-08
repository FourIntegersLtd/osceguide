"""A background job that fails must leave a trace a person can see and a way to run it again.

Three checks, each failing with its list of offenders:

1. Every registered task is classified. A task either records its own failure on the row somebody
   is waiting on (`STATE`, and a test below forces the exception and reads the row), or is in
   `NO_OWN_STATE` with the reason a failure there is safe. A new task is in neither, so the build
   fails until its author decides.
2. For every task, a failed queue row can be retried by staff (`POST /platform/jobs/{id}/retry`);
   a marking goes back through its attempt (`POST /platform/attempts/{id}/rescore`).
3. No service or job code catches an exception, logs it and carries on without writing any state
   or re-raising. Existing sites are in `LOG_ONLY_HANDLERS` with a reason; the ceiling only shrinks.
"""

from __future__ import annotations

import ast
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import jobs
from app.core.events import PENDING_KEY, user_topic
from app.core.jobs import defer_in_transaction
from tests.guards._scan import APP_ROOT, assert_allow_list, parse, python_files, rel
from tests.support.media_production import a_summary
from tests.support.peer_practice import stopped_pair
from tests.support.sittings import org_with_admin
from tests.support.station_imports import IMPORTS, upload_import
from tests.support.tokens import bearer

# --- 1. Every task says how its failure becomes visible ----------------------------------------

# Tasks that write the failure onto the row a person is waiting on. `None`: a test below forces the
# exception and reads the row. A path: that existing test proves it (the guard checks it exists).
STATE: dict[str, str | None] = {
    "score_attempt": None,
    "extract_cv": None,
    "produce_summary_podcast": None,
    "transcribe_peer_session": None,
    "draft_import_template": None,
    "reply_as_assistant": (
        "tests/repository/test_community_assistant.py::test_a_failing_draft_fails_the_run_and_posts_nothing"
    ),
    "deliver_outbound_messages": (
        "tests/http/test_platform_ops_routes.py::"
        "test_mail_abandoned_in_an_outage_is_listed_and_sent_again_on_retry"
    ),
    "record_database_size": (
        "tests/repository/test_health_database_size.py::"
        "test_a_failing_reading_is_written_to_the_audit_log_not_lost"
    ),
    "prune_job_history": (
        "tests/repository/test_health_database_size.py::"
        "test_a_failing_prune_is_written_to_the_audit_log_not_lost"
    ),
}

# Tasks whose service catches every failure and writes it on the row (the handlers are visible in
# the AST lint below), but whose failure no test here forces yet. The number only shrinks.
STATE_NOT_YET_FORCED: dict[str, str] = {
    "draft_import_station": "same _run_step as draft_import_template, which is forced",
    "regenerate_slide_av": "run_slide_av_job marks the item failed; needs a rendered deck to force",
    "produce_podcast_audio": "run_podcast_audio_job marks the item failed; needs a scripted podcast to force",
    "write_media_script": "run_script_write_job marks the item failed; needs the writer model seam",
    "check_media_facts": "run_fact_check_job keeps the error on the item; needs the guideline seams",
    "check_station_facts": "run_check keeps the error on the version; needs the guideline seams",
    "produce_media": "run_produce_job settles the run on the item; needs the agent kit",
    "produce_station": "run_produce_job settles the run on the version; needs the agent kit",
}
STATE_NOT_YET_FORCED_CEILING = 8

# Tasks with no row of their own to mark. The queue row itself ends `failed` and shows in
# `/platform/jobs?status=failed`; the next tick or sweep tries again. The number only shrinks.
NO_OWN_STATE: dict[str, str] = {
    "advance_circuit": (
        "the sweep (every minute) re-drives any circuit past its phase end; a stuck circuit shows on the "
        "live board"
    ),
    "sweep_circuits": "periodic, each circuit's step is isolated and logged; the next minute runs it again",
    "clear_room_agents": "best-effort LiveKit cleanup with its own retry strategy; nobody waits on it",
    "compact_transcripts": "periodic, idempotent; the next tick retries",
    "check_partner_spend": "periodic alert; a missed day is caught by the next daily run",
    "erase_closed_accounts": "periodic; an account that fails stays due and is retried by the next run",
    "expire_practice_queue": "periodic, idempotent; stale places are expired by the next minute's run",
    "match_practice_queue": "periodic, idempotent; waiting people are matched by the next minute's run",
    "try_match_practice_room": "a nudge after a join; match_practice_queue is the safety net",
    "reclaim_stalled_jobs": (
        "the queue's own sweep; a failed run records a sweep.failed audit row and runs again in five minutes"
    ),
    "reindex_material": (
        "periodic; the index catches up on the next run, the tutor only answers from older material meanwhile"
    ),
    "reindex_media_item": "a fast path for the nightly reindex, which covers the same item",
    "send_engagement_emails": "periodic; the email is a nudge, not owed",
    "send_exam_day_reminders": (
        "periodic hourly; each person is reminded once, a missed hour is picked up by the next"
    ),
    "send_invitation_reminders": "periodic; the reminder is a nudge and the invitation itself is unaffected",
    "send_marketplace_session_reminders": (
        "periodic every five minutes, claims sessions in the reminder window"
    ),
    "summarise_assistant_session": (
        "tutor memory: an unsummarised session keeps its turns and is retried; no learner screen waits on it"
    ),
    "summarise_debrief": "tutor memory: the debrief itself is already shown; the summary is background",
    "suspend_lapsed_organizations": (
        "periodic hourly; an organisation not yet suspended is suspended by the next run"
    ),
    "update_attempt_coverage": (
        "a provisional panel recomputed from the committed transcript on the next turn, and at marking"
    ),
    "warn_expiring_access": "periodic hourly; the warning window is a week wide",
}
# 21: `compact_transcripts` is periodic and idempotent, writes no row anyone waits on, and so belongs
# here rather than in STATE (which means "writes the failure on the row a person is waiting on").
NO_OWN_STATE_CEILING = 21


def test_every_registered_task_says_how_its_failure_is_seen() -> None:
    registered = jobs.registered_task_names()
    known = STATE.keys() | STATE_NOT_YET_FORCED.keys() | NO_OWN_STATE.keys()
    unclassified = sorted(registered - known)
    stale = sorted(known - registered)
    both = sorted(NO_OWN_STATE.keys() & (STATE.keys() | STATE_NOT_YET_FORCED.keys()))
    assert not unclassified, (
        f"{unclassified} are registered but not in STATE, STATE_NOT_YET_FORCED or NO_OWN_STATE. "
        "A job that fails must write the failure on the row someone is waiting on "
        "(add a forced-failure test) or say why no one waits."
    )
    assert not stale and not both, f"names no longer registered: {stale}; in both lists: {both}"


def test_the_no_own_state_lists_only_shrink() -> None:
    registered = jobs.registered_task_names()
    assert_allow_list("STATE_NOT_YET_FORCED", STATE_NOT_YET_FORCED, STATE_NOT_YET_FORCED_CEILING, registered)
    assert_allow_list("NO_OWN_STATE", NO_OWN_STATE, NO_OWN_STATE_CEILING, registered)


def test_every_named_proof_test_exists() -> None:
    missing = []
    for name, proof in STATE.items():
        if proof is None:
            continue
        path, _, test = proof.partition("::")
        file = APP_ROOT.parent / path
        if not file.exists() or f"def {test}(" not in file.read_text(encoding="utf-8"):
            missing.append(f"{name}: {proof}")
    assert not missing, f"the test that proves these jobs fail visibly is gone: {missing}"


# --- 2. Staff can retry ------------------------------------------------------------------------

pytestmark_db = pytest.mark.db


def test_the_staff_retry_routes_exist_and_are_platform_admin_only() -> None:
    from app.main import app

    routes = {(m, r.path) for r in app.routes for m in getattr(r, "methods", ()) if hasattr(r, "path")}
    needed = {
        ("POST", "/api/v1/platform/jobs/{job_id}/retry"),
        ("POST", "/api/v1/platform/attempts/{attempt_id}/rescore"),
        ("POST", "/api/v1/platform/outbox/{message_id}/retry"),
    }
    assert needed <= routes, f"missing staff retry routes: {sorted(needed - routes)}"


@pytest.mark.db
async def test_every_failed_task_can_be_retried_by_staff_or_goes_back_through_its_attempt(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    stuck: list[str] = []
    for task in sorted(jobs.registered_task_names()):
        if task == "score_attempt":
            continue
        await defer_in_transaction(db_session, queue="default", task=task, queueing_lock=None, args={})
        job_id = int((await db_session.execute(text("SELECT max(id) FROM procrastinate_jobs"))).scalar_one())
        await db_session.execute(
            text("UPDATE procrastinate_jobs SET status = 'failed' WHERE id = :id"), {"id": job_id}
        )
        response = await client.post(f"/api/v1/platform/jobs/{job_id}/retry", headers=bearer(root))
        status = (
            await db_session.execute(
                text("SELECT status FROM procrastinate_jobs WHERE id = :id"), {"id": job_id}
            )
        ).scalar_one()
        if response.status_code != 204 or status != "todo":
            stuck.append(f"{task}: {response.status_code} {status}")
    assert not stuck, f"staff cannot retry a failed run of: {stuck}"


# --- 3. A forced exception ends in a terminal, visible state -----------------------------------


def _session_opener(session: AsyncSession) -> Any:
    @asynccontextmanager
    async def opener() -> AsyncIterator[AsyncSession]:
        yield session

    return opener


def _tells_the_owner(session: AsyncSession, topic: str) -> bool:
    return any(entry[0] == topic for entry in session.info.get(PENDING_KEY, []))


@pytest.mark.db
async def test_marking_that_keeps_failing_says_so_on_the_attempt(db_session: AsyncSession) -> None:
    from app.features.attempts import repository
    from app.features.attempts.domain import SCORING_FAILED
    from app.features.attempts.jobs import score_attempt_job
    from tests.repository.test_scoring_job import completed_attempt

    attempt_id = await completed_attempt(db_session)

    def exploding_evaluator() -> Any:
        raise RuntimeError("model unreachable")

    await score_attempt_job(
        attempt_id,
        build_evaluator=exploding_evaluator,
        policy_version="platform-default@1",
        framework_id="sca-rcgp-v1",
        now=datetime.now(UTC),
        last_try=True,
        open_session=_session_opener(db_session),
    )

    attempt = await repository.attempt_by_id(db_session, attempt_id)
    assert attempt is not None
    assert attempt.failed_reason == SCORING_FAILED
    assert _tells_the_owner(db_session, user_topic(attempt.user_id))


@pytest.mark.db
async def test_a_cv_read_that_blows_up_is_failed_on_its_row(db_session: AsyncSession, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import openai

    from app.core.settings import get_settings
    from app.features.cv import domain, repository
    from app.features.identity import repository as identity_repository

    monkeypatch.setattr(get_settings(), "openai_api_key", "sk-test")

    class Exploding:
        def __init__(self, **_: Any) -> None:
            raise RuntimeError("openai down")

    monkeypatch.setattr(openai, "AsyncOpenAI", Exploding)
    monkeypatch.setattr("app.core.db.job_session", _session_opener(db_session))
    user = await identity_repository.create_user(
        db_session, email="cv-fail@example.com", name="Dr", password_hash=None
    )
    row = await repository.create(
        db_session, user_id=user.id, original_filename="CV.pdf", extracted_text="x" * 60
    )
    await db_session.flush()
    run = jobs.get_jobs_app().tasks["extract_cv"].func

    await run(str(row.id))

    refreshed = await repository.get(db_session, row.id)
    assert refreshed is not None
    assert refreshed.status == domain.Status.FAILED.value
    assert refreshed.error
    assert _tells_the_owner(db_session, user_topic(user.id))


@pytest.mark.db
async def test_a_podcast_render_that_blows_up_is_failed_on_its_item(
    client: AsyncClient, make_actor, db_session: AsyncSession, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    from app.features.identity import repository as identity_repository
    from app.features.media_production import podcast_tts
    from app.features.media_production.service import MEDIA_UPDATED, production_item

    email = "job-podcast@osceguide.com"
    admin = await make_actor(email, platform_admin=True)
    item = await a_summary(client, admin)
    media_id = uuid.UUID(item["id"])
    user = await identity_repository.user_by_email(db_session, email)
    assert user is not None

    def boom(*_: Any, **__: Any) -> None:
        raise RuntimeError("tts down")

    monkeypatch.setattr(podcast_tts, "produce_summary_podcast", boom)
    monkeypatch.setattr("app.core.db.job_session", _session_opener(db_session))
    run = jobs.get_jobs_app().tasks["produce_summary_podcast"].func

    await run(str(media_id), str(user.id))

    assert (await production_item(db_session, media_id)).content["status"] == "failed"
    assert (user_topic(user.id), MEDIA_UPDATED, {"media_id": str(media_id)}) in db_session.info[PENDING_KEY]


@pytest.mark.db
async def test_an_import_draft_that_blows_up_is_failed_on_its_import(
    client: AsyncClient, make_actor, db_session: AsyncSession, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    from app.features.stations import station_import_drafting

    _, admin = await org_with_admin(client, make_actor)
    import_id = (await upload_import(client, admin)).json()["id"]
    db_session.info.pop(PENDING_KEY, None)

    async def boom(*_: Any, **__: Any) -> None:
        raise RuntimeError("model exploded")

    monkeypatch.setattr(station_import_drafting, "parse_ai_structured", boom)
    monkeypatch.setattr("app.core.db.job_session", _session_opener(db_session))
    run = jobs.get_jobs_app().tasks["draft_import_template"].func

    await run(import_id)

    queued = [name for _topic, name, _payload in db_session.info.get(PENDING_KEY, [])]
    assert queued == ["station_import.updated"]
    failed = (await client.get(f"{IMPORTS}/{import_id}", headers=bearer(admin))).json()
    assert failed["status"] == "failed"
    assert failed["error"]


@pytest.mark.db
async def test_a_transcription_job_that_blows_up_is_failed_on_its_session(
    client: AsyncClient, make_actor, db_session: AsyncSession, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    from app.features.peer_practice import repository_sessions, service_feedback

    row = await stopped_pair(client, make_actor, db_session, "job-fail")
    session_id = row.id

    async def boom(*_: Any, **__: Any) -> None:
        raise RuntimeError("marking pipeline down")

    monkeypatch.setattr(service_feedback, "build_feedback", boom)
    monkeypatch.setattr("app.core.db.job_session", _session_opener(db_session))
    run = jobs.get_jobs_app().tasks["transcribe_peer_session"].func

    await run(str(session_id))

    refreshed = await repository_sessions.session_by_id(db_session, session_id)
    assert refreshed is not None
    assert refreshed.recording_state == "failed"
    assert refreshed.recording_error


# --- 4. No catch-log-and-carry-on ---------------------------------------------------------------

_LOG_METHODS = {"debug", "info", "warning", "warn", "error", "exception", "critical"}
_LOGGERS = {"log", "logger", "logging"}

# `file::function`: handlers that log and carry on without writing state. The ceiling only shrinks.
LOG_ONLY_HANDLERS: dict[str, str] = {
    "app/features/sittings/service_floor.py::apply": (
        "best effort: every token carries the rule, so a rejoin corrects a missed update"
    ),
    "app/features/assistant/service_knowledge.py::_material": (
        "optional context for a spoken answer; falling back to none is the design"
    ),
    "app/features/attempts/service_render.py::_marking_snapshot": (
        "returns None and the caller refuses the render with its own code"
    ),
    "app/features/attempts/service_trial.py::trial_stream": (
        "yields a failed snapshot to the stream before returning; the stream is the visible state"
    ),
    "app/features/health/service.py::_answers_in_time": (
        "the health report is the visible state: it answers error"
    ),
    "app/features/identity/service_erasure.py::erase_due_accounts": (
        "the account stays due and the next daily run retries it; log.exception reaches Sentry"
    ),
    "app/features/media_production/service_facts.py::report": (
        "a progress save; the final review is stored at the end of the check"
    ),
    "app/features/peer_practice/service_recording.py::stop_recording_and_queue": (
        "audio may still have been written, so transcription proceeds regardless"
    ),
    "app/features/sittings/jobs.py::_one_circuit": (
        "one circuit failing must not stop the sweep; the next minute retries it"
    ),
    "app/features/sittings/service_catchup.py::advance_due": (
        "a read-time catch-up; the sweep job is the owner of the transition"
    ),
    "app/features/tutor_memory/service_search.py::_material": (
        "the tutor is told the search did not run, not that nothing was found"
    ),
    "app/features/tutor_memory/service_search.py::_guidelines": (
        "optional passages within the voice loop's time budget"
    ),
    "app/features/tutor_memory/service_session.py::render_dashboard_session": (
        "falls back to placeholder instructions so the session still starts"
    ),
    "app/features/voice/service.py::leave_queue": (
        "best-effort publish after the leave already succeeded; the waiter expires anyway"
    ),
}
LOG_ONLY_CEILING = 14


def _is_log_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _LOG_METHODS
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in _LOGGERS
    )


def log_only_handlers(path: Path) -> list[tuple[str, int]]:
    """`(function, line)` of each `except` that logs, writes nothing and does not re-raise.

    "Writes" is any await, any assignment (a value later saved, as `_run_step` does) or any raise.
    What is left is a handler whose only effect is a log line.
    """
    found: dict[int, str] = {}
    for function in ast.walk(parse(path)):
        if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for handler in (n for n in ast.walk(function) if isinstance(n, ast.ExceptHandler)):
            body = [x for statement in handler.body for x in ast.walk(statement)]
            if not any(_is_log_call(x) for x in body):
                continue
            acts = (ast.Raise, ast.Await, ast.Assign, ast.AugAssign, ast.AnnAssign)
            if any(isinstance(x, acts) for x in body):
                continue
            found[handler.lineno] = function.name  # walk is outer-first: the innermost wins
    return sorted((name, line) for line, name in found.items())


def _job_and_service_files() -> list[Path]:
    return [
        p for p in python_files(APP_ROOT) if p.name.startswith(("jobs", "service")) or "worker" in p.parts
    ]


def test_no_handler_only_logs() -> None:
    offenders = sorted(
        {f"{rel(path)}::{name}" for path in _job_and_service_files() for name, _ in log_only_handlers(path)}
        - LOG_ONLY_HANDLERS.keys()
    )
    assert not offenders, (
        f"{offenders} catch an exception, log it and carry on. Write the failure onto the row or "
        "re-raise so the queue retries; if neither is right, add the function to LOG_ONLY_HANDLERS "
        "with the reason."
    )


def test_the_log_only_allow_list_only_shrinks() -> None:
    seen = {f"{rel(p)}::{name}" for p in _job_and_service_files() for name, _ in log_only_handlers(p)}
    assert_allow_list("LOG_ONLY_HANDLERS", LOG_ONLY_HANDLERS, LOG_ONLY_CEILING, seen)


def test_the_lint_catches_a_log_only_handler(tmp_path: Path) -> None:
    bad = tmp_path / "service.py"
    bad.write_text(
        "async def f():\n    try:\n        await g()\n    except Exception:\n        log.exception('x')\n",
        encoding="utf-8",
    )
    good = tmp_path / "service_ok.py"
    good.write_text(
        "async def f():\n    try:\n        await g()\n    except Exception:\n        log.exception('x')\n"
        "        await set_failed()\n",
        encoding="utf-8",
    )
    assert log_only_handlers(bad) == [("f", 4)]
    assert log_only_handlers(good) == []
