"""Pieces the e2e tests share: a stub backend, a fake candidate, a worker subprocess."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import uuid
import wave
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiohttp import web
from livekit import api, rtc
from livekit.protocol.agent_dispatch import CreateAgentDispatchRequest

from osce_assessment.contracts import (
    AIInteractionProfile, AssessmentAttempt, AssessmentDefinition, EvaluationPolicy, InteractionMode, Scenario, ScenarioRef, ScenarioSource,
)

ROOT = Path(__file__).resolve().parents[2]


def rendered_attempt(attempt_id: str, candidate_ref: str) -> tuple[AssessmentAttempt, Scenario]:
    scenario = Scenario(id="e2e-station", source=ScenarioSource.INLINE, title="E2E chest pain", patient_gender="Female")
    profile = AIInteractionProfile(
        mode=InteractionMode.PATIENT,
        instructions="You are a patient with chest tightness. Answer the doctor's questions briefly, in one or two sentences.",
        greeting="Hello doctor, I'm ready when you are.",
    )
    definition = AssessmentDefinition(
        id="e2e-def", version="1", framework_id="sca-rcgp-v1",
        scenario_ref=ScenarioRef(source=ScenarioSource.INLINE, scenario_id="e2e-station"),
        interaction_profile=profile,
        evaluation_policy=EvaluationPolicy(framework_id="sca-rcgp-v1", primary_model="none"),
        snapshot_at=datetime.now(timezone.utc),
    )
    return AssessmentAttempt(attempt_id=attempt_id, definition=definition, candidate_ref=candidate_ref), scenario


@dataclass
class StubBackend:
    """Serves the bootstrap route and records what the worker posts back."""

    attempt_id: str
    candidate_ref: str
    chunks: list[dict[str, Any]] = field(default_factory=list)
    completes: list[dict[str, Any]] = field(default_factory=list)
    slot_calls: list[str] = field(default_factory=list)
    base_url: str = ""
    _runner: web.AppRunner | None = None

    async def start(self) -> None:
        app = web.Application()
        attempt, scenario = rendered_attempt(self.attempt_id, self.candidate_ref)

        async def bootstrap(request):
            if request.match_info["attempt_id"] != self.attempt_id:
                return web.json_response({"error": "not found"}, status=404)
            return web.json_response({"attempt": attempt.model_dump(mode="json"), "scenario": scenario.model_dump(mode="json")})

        async def chunk(request):
            self.chunks.append(await request.json())
            return web.json_response({"ok": True})

        async def complete(request):
            self.completes.append(await request.json())
            return web.json_response({"ok": True})

        async def slot(request):
            self.slot_calls.append(request.path)
            return web.json_response({"ok": True})

        app.router.add_get("/api/worker/attempts/{attempt_id}", bootstrap)
        app.router.add_post("/api/worker/attempts/{attempt_id}/transcript-chunks", chunk)
        app.router.add_post("/api/worker/attempts/{attempt_id}/transcript", complete)
        app.router.add_post("/slot/release", slot)
        app.router.add_post("/slot/extend", slot)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]  # noqa: SLF001 — aiohttp exposes no public accessor
        self.base_url = f"http://127.0.0.1:{port}"

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()


@dataclass
class WorkerProcess:
    agent_name: str
    backend_url: str
    env: dict[str, str]
    candidate_timeout_s: float = 20.0
    proc: subprocess.Popen | None = None

    def start(self) -> None:
        backends = {"e2e": {"base_url_env": "E2E_BACKEND_URL", "secret_env": "E2E_SECRET", "secret_header": "X-E2E-Secret",
                            "slot_release_path": "/slot/release", "slot_extend_path": "/slot/extend", "slot_payload_key": "room_name"}}
        env = {
            **os.environ,
            "PYTHONPATH": str(ROOT / "packages"),
            "LIVEKIT_URL": self.env["LIVEKIT_E2E_URL"], "LIVEKIT_API_KEY": self.env["LIVEKIT_E2E_KEY"], "LIVEKIT_API_SECRET": self.env["LIVEKIT_E2E_SECRET"],
            "VOICE_BACKENDS_JSON": json.dumps(backends), "E2E_BACKEND_URL": self.backend_url, "E2E_SECRET": "e2e",
            "LIVEKIT_ASSESSMENT_AGENT_NAME": self.agent_name, "LIVEKIT_ASSESSMENT_CANDIDATE_TIMEOUT_S": str(self.candidate_timeout_s),
            "SENTRY_DSN": "",
        }
        self.proc = subprocess.Popen([sys.executable, "-m", "livekit_assessment_worker.entrypoint", "start"], env=env, cwd=ROOT)

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def token(env: dict[str, str], identity: str, room: str) -> str:
    return api.AccessToken(env["LIVEKIT_E2E_KEY"], env["LIVEKIT_E2E_SECRET"]).with_identity(identity).with_grants(api.VideoGrants(room_join=True, room=room)).to_jwt()


async def dispatch(env: dict[str, str], *, agent_name: str, room: str, metadata: dict[str, Any]) -> None:
    async with api.LiveKitAPI(env["LIVEKIT_E2E_URL"], env["LIVEKIT_E2E_KEY"], env["LIVEKIT_E2E_SECRET"]) as lk:
        await lk.agent_dispatch.create_dispatch(CreateAgentDispatchRequest(agent_name=agent_name, room=room, metadata=json.dumps(metadata)))


async def play_wav(room: rtc.Room, wav_path: str) -> None:
    """Publish the WAV as the participant's microphone, in real time."""
    with wave.open(wav_path, "rb") as wav:
        assert wav.getnchannels() == 1 and wav.getsampwidth() == 2, "16-bit mono PCM required"
        sample_rate = wav.getframerate()
        pcm = wav.readframes(wav.getnframes())
    source = rtc.AudioSource(sample_rate, 1)
    track = rtc.LocalAudioTrack.create_audio_track("mic", source)
    await room.local_participant.publish_track(track, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))
    samples_per_frame = sample_rate // 100  # 10 ms
    step = samples_per_frame * 2
    for offset in range(0, len(pcm), step):
        chunk = pcm[offset:offset + step]
        if len(chunk) < step:
            chunk = chunk + b"\x00" * (step - len(chunk))
        await source.capture_frame(rtc.AudioFrame(data=chunk, sample_rate=sample_rate, num_channels=1, samples_per_channel=samples_per_frame))
        await asyncio.sleep(0.01)


async def candidate_session(env: dict[str, str], *, room_name: str, identity: str, wav_path: str, linger_s: float) -> list[str]:
    """Join, wait for the agent, play the audio, linger, leave. Returns the agent identities seen."""
    room = rtc.Room()
    await room.connect(env["LIVEKIT_E2E_URL"], token(env, identity, room_name))
    try:
        for _ in range(60):
            if any(p.identity.startswith("agent-") for p in room.remote_participants.values()):
                break
            await asyncio.sleep(0.5)
        await asyncio.sleep(3.0)  # let the greeting play
        await play_wav(room, wav_path)
        await asyncio.sleep(linger_s)
        return sorted(p.identity for p in room.remote_participants.values() if p.identity.startswith("agent-"))
    finally:
        await room.disconnect()


def new_room() -> str:
    return f"e2e_{uuid.uuid4().hex[:10]}"
