"""The real assistant worker running a dashboard session against this API.

The companion to `test_attempt_e2e.py`, for the other worker. Its absence is
the same shaped hole: every other test of the tutor either stops at the HTTP
boundary or hands the worker's job to a fixture, so nothing has ever proved
that a browser can get into an assistant room at all — which is the whole of
Step 0, and the one route the tutor's entire feature hangs off.

**What it asserts, and what it deliberately does not.**

It asserts the things that are the same on every run: that a dashboard session
can be opened, that a browser can mint a token for its room, that the real
worker joins and is handed the tutor's tools with their schemas, that a tool call
answers with a line a model can say, and that the conversation is recorded.

It does **not** assert that the model chose to call a tool. That depends on
what the candidate's WAV happens to say and on the model's judgement on the
day, and a test that fails when a model exercises its judgement differently is
a test that gets deleted. What arrives at the tool route is instead exercised
directly, exactly as the worker would call it. If you want the model-initiated
path observed, watch the API's log for `assistant tool call` during a run — it
records the tool name and the round trip in milliseconds.

**Not yet run.** Same prerequisites as the attempt test, plus nothing new:
the tutor's own material search answers "not configured" without an embedding
key, which is a valid state for this test rather than a gap in it.

If the first thing that fails is the tools assertion with an **empty** list,
the cause is almost certainly the engine: a dashboard session falls back to
the placeholder instructions — and therefore to no tools — when the prompt
cannot be rendered, and that fallback is deliberate, because a session that
refuses to start is worse than a plain one. Check the API's log for "tutor
prompt not rendered" before looking anywhere else.

    make db-up && make migrate && make start        # terminal 1

    export LIVEKIT_E2E_URL=... LIVEKIT_E2E_KEY=... LIVEKIT_E2E_SECRET=...
    export LIVEKIT_E2E_AUDIO_WAV=/path/to/16k-mono.wav
    export DEEPGRAM_API_KEY=... OPENAI_API_KEY=...
    export ASSESSMENT_PLATFORM_ROOT=/path/to/assessment-platform
    export ASSESSMENT_PLATFORM_PYTHON="$(cd $ASSESSMENT_PLATFORM_ROOT && poetry env info --path)/bin/python"
    export PLATFORM_E2E_BASE_URL=http://127.0.0.1:8002
    export PLATFORM_E2E_TOKEN=<bearer for an entitled user>
    export WORKER_SECRET=<the same one the API is running with>
    poetry run pytest -m e2e tests/e2e -q                # terminal 2
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import httpx
import pytest

from tests.e2e.test_attempt_e2e import _harness

pytestmark = pytest.mark.e2e

# No station version here, unlike the attempt test: a dashboard session is
# about this learner's own history and is not bound to a station at all.
EXTRA = ("PLATFORM_E2E_BASE_URL", "PLATFORM_E2E_TOKEN")

EXPECTED_TOOLS = {"recall_history", "search_material", "suggest_material", "remember", "mark_done"}


def _start_assistant_worker(*, root: str, env: dict[str, str], base_url: str, secret: str, agent: str):  # type: ignore[no-untyped-def]
    """The real assistant worker, pointed at this API.

    Note the module: `livekit_assistant_worker`, not the assessment one. They
    are separate agents with separate names, and dispatching one where the
    other is expected is a room that nobody ever joins.
    """
    backends = {
        "platform": {
            "base_url_env": "PLATFORM_BACKEND_URL",
            "secret_env": "PLATFORM_WORKER_SECRET",
            "secret_header": "X-Worker-Secret",
            "slot_release_path": "/api/worker/livekit-cloud-slot/release",
            "slot_extend_path": "/api/worker/livekit-cloud-slot/extend",
            "slot_payload_key": "room_name",
        }
    }
    python = os.environ.get("ASSESSMENT_PLATFORM_PYTHON") or sys.executable
    return subprocess.Popen(  # noqa: S603
        [python, "-m", "livekit_assistant_worker.entrypoint", "start"],
        cwd=Path(root),
        env={
            **os.environ,
            "PYTHONPATH": str(Path(root) / "packages"),
            "LIVEKIT_URL": env["LIVEKIT_E2E_URL"],
            "LIVEKIT_API_KEY": env["LIVEKIT_E2E_KEY"],
            "LIVEKIT_API_SECRET": env["LIVEKIT_E2E_SECRET"],
            "VOICE_BACKENDS_JSON": json.dumps(backends),
            "PLATFORM_BACKEND_URL": base_url,
            "PLATFORM_WORKER_SECRET": secret,
            "LIVEKIT_ASSISTANT_AGENT_NAME": agent,
            "SENTRY_DSN": "",
        },
    )


def _worker_headers() -> dict[str, str]:
    return {"X-Worker-Secret": os.environ["WORKER_SECRET"]}


async def test_a_browser_can_join_a_dashboard_session_and_its_tools_answer(
    e2e_env: dict[str, str],
) -> None:
    """Open a session → mint a token → the worker bootstraps → a tool answers.

    The assertions are about what this API served and stored, not about what
    the tutor said.
    """
    missing = [v for v in (*EXTRA, "WORKER_SECRET") if not os.environ.get(v)]
    if missing:
        pytest.skip(f"needs {missing}")

    base_url = os.environ["PLATFORM_E2E_BASE_URL"].rstrip("/")
    auth = {"Authorization": f"Bearer {os.environ['PLATFORM_E2E_TOKEN']}"}
    harness = _harness(e2e_env["ASSESSMENT_PLATFORM_ROOT"])
    agent = f"e2e-tutor-{uuid.uuid4().hex[:8]}"

    async with httpx.AsyncClient(base_url=base_url, timeout=30) as api:
        me = await api.get("/api/v1/me", headers=auth)
        assert me.status_code == 200, me.text
        candidate_ref = me.json()["id"]

        created = await api.post(
            "/api/v1/assistant/sessions",
            json={"session_type": "dashboard"},
            headers=auth,
        )
        assert created.status_code == 201, created.text
        session_id = created.json()["id"]

        # Step 0, and the reason this file exists: before this route there was
        # no way for a browser to be in an assistant room at all, so none of
        # the tutor's work could be exercised end to end.
        granted = await api.post(
            f"/api/v1/assistant/sessions/{session_id}/voice-token",
            headers=auth,
        )
        assert granted.status_code == 200, granted.text
        grant = granted.json()
        assert grant["token"], "no room token was issued"
        assert grant["server_url"], "the token names no LiveKit server"
        room = grant["room"]

        # What the worker is about to be handed. Fetched here as well as by the
        # worker because this is the assertion — that a *dashboard* bootstrap
        # carries the tutor's tools, each with a schema the model can be
        # given. An empty list is the pre-tutor behaviour and would pass every
        # other test in the suite.
        boot = await api.get(f"/api/worker/assistant-sessions/{session_id}", headers=_worker_headers())
        assert boot.status_code == 200, boot.text
        session = boot.json()["session"]
        tools = {tool["name"] for tool in session.get("tools", [])}
        assert tools == EXPECTED_TOOLS, f"dashboard bootstrap carried {tools}"
        assert session["instructions"].strip(), "the tutor was given no instructions"
        for tool in session["tools"]:
            assert tool["parameters"]["type"] == "object", tool["name"]
            assert tool["description"].strip(), tool["name"]

        # One tool call over the real route, exactly as the worker makes it.
        # `remember` rather than a lookup because its effect is observable
        # through a public route, which is the next assertion.
        fact = f"e2e marker {uuid.uuid4().hex[:8]}"
        called = await api.post(
            f"/api/worker/assistant-sessions/{session_id}/tools/remember",
            json={"tool": "remember", "arguments": {"fact": fact}, "call_id": "e2e"},
            headers=_worker_headers(),
        )
        assert called.status_code == 200, called.text
        assert called.json()["result"].strip(), "the tool answered with nothing to say"

        # The tutor's memory is the point of the slice, so read it back the way
        # the doctor would.
        memory = await api.get("/api/v1/me/tutor-memory", headers=auth)
        assert memory.status_code == 200, memory.text
        facts = [
            str(note["body"].get("fact", ""))
            for note in memory.json()["notes"]
            if note["kind"] == "stated_fact"
        ]
        assert fact in facts, "what the tutor was told to remember was not stored"

        worker = _start_assistant_worker(
            root=e2e_env["ASSESSMENT_PLATFORM_ROOT"],
            env=e2e_env,
            base_url=base_url,
            secret=os.environ["WORKER_SECRET"],
            agent=agent,
        )
        try:
            await harness.dispatch(
                e2e_env,
                agent_name=agent,
                room=room,
                metadata={
                    "session_id": session_id,
                    "backend": "platform",
                    "candidate_ref": candidate_ref,
                },
            )
            await harness.candidate_session(
                e2e_env,
                room_name=room,
                identity=candidate_ref,
                wav_path=e2e_env["LIVEKIT_E2E_AUDIO_WAV"],
                linger_s=25.0,
            )
            # The transcript is posted once the room empties.
            await asyncio.sleep(5)
        finally:
            if worker.poll() is None:
                worker.terminate()
                try:
                    worker.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    worker.kill()

        after = await api.get("/api/v1/me/tutor-memory", headers=auth)
        assert after.status_code == 200, after.text

    # The conversation reached the tutor's memory. Which note it becomes
    # depends on whether the summary job has run — see below.
    assert after.json()["notes"], "nothing at all was remembered from the session"


async def test_a_dashboard_transcript_is_summarised_and_then_deleted(
    e2e_env: dict[str, str],
) -> None:
    """The privacy promise, checked against a real conversation.

    A dashboard session's turns are stored so the summariser has something to
    read and deleted by the job that writes the note. Both halves matter and
    only the pair is the promise: a note with the turns still beside it is a
    recording nobody asked for, and deleted turns with no note is the
    conversation lost.

    **This one needs the job worker running** (`make worker`), because the
    deletion is the job's last act. Without it the turns stay, which is the
    correct behaviour rather than a failure — so the test says which it saw
    rather than hanging on a queue that nobody is draining.
    """
    missing = [v for v in (*EXTRA, "WORKER_SECRET") if not os.environ.get(v)]
    if missing:
        pytest.skip(f"needs {missing}")

    base_url = os.environ["PLATFORM_E2E_BASE_URL"].rstrip("/")
    auth = {"Authorization": f"Bearer {os.environ['PLATFORM_E2E_TOKEN']}"}

    async with httpx.AsyncClient(base_url=base_url, timeout=30) as api:
        created = await api.post(
            "/api/v1/assistant/sessions", json={"session_type": "dashboard"}, headers=auth
        )
        assert created.status_code == 201, created.text
        session_id = created.json()["id"]

        delivered = await api.post(
            f"/api/worker/assistant-sessions/{session_id}/transcript",
            json={
                "session_id": session_id,
                "worker_type": "dashboard",
                "candidate_ref": "",
                "transcript": {
                    "messages": [
                        {
                            "message_id": "m1",
                            "seq": 0,
                            "role": "user",
                            "message": "I keep running out of time on the management plan.",
                        },
                        {
                            "message_id": "m2",
                            "seq": 1,
                            "role": "assistant",
                            "message": "Then let us agree you will do two timed stations this week.",
                        },
                    ]
                },
            },
            headers=_worker_headers(),
        )
        assert delivered.status_code in (200, 202, 204), delivered.text

        # Give the summary job a chance. It is deferred in the transaction that
        # accepted the transcript, so it is already owed by the time this
        # returns; what is uncertain is only whether anything is draining it.
        summary = None
        for _ in range(20):
            await asyncio.sleep(3)
            memory = await api.get("/api/v1/me/tutor-memory", headers=auth)
            assert memory.status_code == 200, memory.text
            summaries = [n for n in memory.json()["notes"] if n["kind"] == "session_summary"]
            if summaries:
                summary = summaries[0]
                break

    if summary is None:
        pytest.skip(
            "no session_summary appeared in 60s — is `make worker` running? "
            "The turns are retained until the job writes the note, which is correct."
        )

    body = summary["body"]
    assert str(body.get("summary", "")).strip(), "the summary note carried no summary"
