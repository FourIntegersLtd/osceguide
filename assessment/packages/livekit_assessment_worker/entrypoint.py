"""LiveKit worker entrypoint for the assessment worker."""

from __future__ import annotations

from dotenv import load_dotenv
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.plugins import deepgram, noise_cancellation  # noqa: F401 — plugin registration

from voice_infra import BackendRegistry
from voice_infra.sentry import init_sentry, raise_sentry_verify_error_if_requested
from voice_infra.worker_config import (
    optional_float,
    required_agent_name,
    validate_speech_credentials,
    worker_port,
)
from voice_infra.worker_load import concurrent_job_load_settings

from .session import AssessmentSession

WORKER_NAME = "assessment"
AGENT_NAME_ENV = "LIVEKIT_ASSESSMENT_AGENT_NAME"
PORT_ENV = "LIVEKIT_ASSESSMENT_WORKER_PORT"
MAX_JOBS_ENV = "LIVEKIT_ASSESSMENT_MAX_CONCURRENT_JOBS"
LOAD_THRESHOLD_ENV = "LIVEKIT_ASSESSMENT_LOAD_THRESHOLD"
DRAIN_TIMEOUT_ENV = "LIVEKIT_ASSESSMENT_DRAIN_TIMEOUT"
DEFAULT_PORT = 8087
# Seconds the worker keeps draining after SIGTERM before it stops waiting on
# running jobs. Must stay under the pod's terminationGracePeriodSeconds (900s
# in k8s/) or the kubelet SIGKILLs mid-session; the SDK default is one hour.
DEFAULT_DRAIN_TIMEOUT = 840


def validate_environment() -> BackendRegistry:
    """Fail fast: backends must be configured, and the Deepgram key too unless on LiveKit Cloud."""
    validate_speech_credentials()
    return BackendRegistry.from_env()


async def _entrypoint(ctx: JobContext) -> None:
    """Module-level so LiveKit can pickle the entrypoint for job subprocesses (macOS spawn)."""
    await AssessmentSession(BackendRegistry.from_env()).entrypoint(ctx)


def build_worker_options() -> WorkerOptions:
    """Check the environment and build the LiveKit worker options from it."""
    validate_environment()

    options: dict = {
        "entrypoint_fnc": _entrypoint,
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
    """Command line entry: load settings, start error reporting and run the worker."""
    load_dotenv()
    init_sentry(worker=WORKER_NAME)
    raise_sentry_verify_error_if_requested()
    cli.run_app(build_worker_options())


if __name__ == "__main__":
    cli_main()
