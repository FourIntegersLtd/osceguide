"""The real assessment worker against a running platform-api, end to end.

This is the test whose absence let `attempts.definition` stay unwritten for the
whole build: every other test either wrote the definition itself or stopped at
the HTTP boundary, so nothing ever proved a worker could start a session.

It drives a **running** API over HTTP rather than booting one in a fixture, so
there is nothing clever to go wrong and it matches how the stack is actually
run: `make db-up && make migrate && make start`, plus Redis and the worker.
Everything it asserts is read back through the public API.

It reuses `assessment-platform/tests/e2e/_harness.py` for the LiveKit parts —
token minting, dispatch, playing a WAV as the candidate — because that harness
is already proven against the worker.

**Not yet run.** It needs a LiveKit project, Deepgram and OpenAI keys, a
sibling `assessment-platform` checkout and a live API; I had none of those, so
treat the first run as part of the test rather than a formality.

    make db-up && make migrate && make start        # terminal 1

    export LIVEKIT_E2E_URL=... LIVEKIT_E2E_KEY=... LIVEKIT_E2E_SECRET=...
    export LIVEKIT_E2E_AUDIO_WAV=/path/to/16k-mono.wav
    export DEEPGRAM_API_KEY=... OPENAI_API_KEY=...
    export ASSESSMENT_PLATFORM_ROOT=/path/to/assessment-platform
    export PLATFORM_E2E_BASE_URL=http://127.0.0.1:8002
    export PLATFORM_E2E_TOKEN=<bearer for an entitled user>
    export PLATFORM_E2E_STATION_VERSION_ID=<a published station version>
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
from typing import Any

import httpx
import pytest

pytestmark = pytest.mark.e2e

EXTRA = ("PLATFORM_E2E_BASE_URL", "PLATFORM_E2E_TOKEN", "PLATFORM_E2E_STATION_VERSION_ID")


def _harness(root: str) -> Any:
    """Import the worker's own e2e harness rather than reimplementing it."""
    path = Path(root)
    for entry in (str(path), str(path / "packages")):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    from tests.e2e import _harness as harness  # type: ignore[import-not-found]

    return harness


def _start_worker(*, root: str, env: dict[str, str], base_url: str, secret: str, agent: str):  # type: ignore[no-untyped-def]
    """The real worker, pointed at this API instead of the harness's stub."""
    backends = {
        "platform": {
            "base_url_env": "PLATFORM_BACKEND_URL",
            "secret_env": "PLATFORM_WORKER_SECRET",
            # Must match `settings.worker_secret_header`, or every call is a 401.
            "secret_header": "X-Worker-Secret",
            "slot_release_path": "/api/worker/livekit-cloud-slot/release",
            "slot_extend_path": "/api/worker/livekit-cloud-slot/extend",
            "slot_payload_key": "room_name",
        }
    }
    return subprocess.Popen(  # noqa: S603
        [sys.executable, "-m", "livekit_assessment_worker.entrypoint", "start"],
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
            "LIVEKIT_ASSESSMENT_AGENT_NAME": agent,
            "SENTRY_DSN": "",
        },
    )


async def test_the_real_worker_runs_an_attempt_created_by_this_api(
    e2e_env: dict[str, str],
) -> None:
    """Create over HTTP → dispatch → the worker bootstraps here → turns land.

    The assertions are about what this API stored, not about what the worker
    said: what matters is that the conversation was recorded against the
    attempt and that it is left ready to mark.
    """
    missing = [v for v in EXTRA if not os.environ.get(v)]
    if missing:
        pytest.skip(f"needs {missing}")

    base_url = os.environ["PLATFORM_E2E_BASE_URL"].rstrip("/")
    auth = {"Authorization": f"Bearer {os.environ['PLATFORM_E2E_TOKEN']}"}
    harness = _harness(e2e_env["ASSESSMENT_PLATFORM_ROOT"])
    agent = f"e2e-{uuid.uuid4().hex[:8]}"

    async with httpx.AsyncClient(base_url=base_url, timeout=30) as api:
        # The worker joins as the candidate, and the bootstrap names them by
        # user id. `AttemptRead` does not carry it, so ask who the token is.
        me = await api.get("/api/v1/me", headers=auth)
        assert me.status_code == 200, me.text
        candidate_ref = me.json()["id"]

        created = await api.post(
            "/api/v1/attempts",
            json={
                "kind": "practice",
                "exam_code": "sca",
                "station_version_id": os.environ["PLATFORM_E2E_STATION_VERSION_ID"],
            },
            headers=auth,
        )
        assert created.status_code == 201, created.text
        attempt_id = created.json()["id"]

        worker = _start_worker(
            root=e2e_env["ASSESSMENT_PLATFORM_ROOT"],
            env=e2e_env,
            base_url=base_url,
            secret=os.environ["WORKER_SECRET"],
            agent=agent,
        )
        room = harness.new_room()
        try:
            await harness.dispatch(
                e2e_env,
                agent_name=agent,
                room=room,
                metadata={
                    "attempt_id": attempt_id,
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
            # The completed transcript is posted after the room empties.
            await asyncio.sleep(5)
        finally:
            if worker.poll() is None:
                worker.terminate()
                try:
                    worker.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    worker.kill()

        transcript = await api.get(f"/api/v1/attempts/{attempt_id}/transcript", headers=auth)
        assert transcript.status_code == 200, transcript.text
        body = transcript.json()

    assert body["messages"], "the worker delivered no turns"
    assert body["complete"] is True, "the completed transcript never arrived"
