"""LiveKit worker entrypoint for the assistant worker."""

from __future__ import annotations

from dotenv import load_dotenv
from livekit.agents import JobContext, JobProcess, WorkerOptions, cli
from livekit.plugins import deepgram, noise_cancellation  # noqa: F401 — plugin registration
from voice_infra import BackendRegistry
from voice_infra.gpt_live import build_gpt_live_vad
from voice_infra.sentry import init_sentry, raise_sentry_verify_error_if_requested
from voice_infra.worker_config import (
    optional_float,
    required_agent_name,
    required_deepgram_api_key,
    worker_port,
)
from voice_infra.worker_load import concurrent_job_load_settings

from .runtime_policy import gpt_live_enabled
from .session import AssistantVoiceSession

WORKER_NAME = "assistant"
AGENT_NAME_ENV = "LIVEKIT_ASSISTANT_AGENT_NAME"
PORT_ENV = "LIVEKIT_ASSISTANT_WORKER_PORT"
MAX_JOBS_ENV = "LIVEKIT_ASSISTANT_MAX_CONCURRENT_JOBS"
LOAD_THRESHOLD_ENV = "LIVEKIT_ASSISTANT_LOAD_THRESHOLD"
DRAIN_TIMEOUT_ENV = "LIVEKIT_ASSISTANT_DRAIN_TIMEOUT"
DEFAULT_PORT = 8088
# Seconds the worker keeps draining after SIGTERM before it stops waiting on
# running jobs. Must stay under the pod's terminationGracePeriodSeconds (900s
# in k8s/) or the kubelet SIGKILLs mid-session; the SDK default is one hour.
DEFAULT_DRAIN_TIMEOUT = 840


def prewarm(proc: JobProcess) -> None:
    if gpt_live_enabled():
        proc.userdata["gpt_live_vad"] = build_gpt_live_vad()


def validate_environment() -> BackendRegistry:
    required_deepgram_api_key()
    return BackendRegistry.from_env()


async def _entrypoint(ctx: JobContext) -> None:
    """Module-level so LiveKit can pickle the entrypoint for job subprocesses (macOS spawn)."""
    await AssistantVoiceSession(BackendRegistry.from_env()).entrypoint(ctx)


def build_worker_options() -> WorkerOptions:
    validate_environment()

    options: dict = {
        "entrypoint_fnc": _entrypoint,
        "prewarm_fnc": prewarm,
        "agent_name": required_agent_name(AGENT_NAME_ENV),
        "port": worker_port(PORT_ENV, DEFAULT_PORT),
        "drain_timeout": int(optional_float(DRAIN_TIMEOUT_ENV, DEFAULT_DRAIN_TIMEOUT)),
    }
    load_fnc, load_threshold = concurrent_job_load_settings(max_jobs_env=MAX_JOBS_ENV, threshold_env=LOAD_THRESHOLD_ENV)
    if load_fnc is not None:
        options["load_fnc"] = load_fnc
        options["load_threshold"] = load_threshold
    return WorkerOptions(**options)


def cli_main() -> None:
    load_dotenv()
    init_sentry(worker=WORKER_NAME)
    raise_sentry_verify_error_if_requested()
    cli.run_app(build_worker_options())


if __name__ == "__main__":
    cli_main()
