"""Sentry error and tracing init for voice worker processes."""

from __future__ import annotations

import os
import sys
from typing import Any

import sentry_sdk
from dotenv import load_dotenv
from sentry_sdk.integrations.anthropic import AnthropicIntegration
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.openai import OpenAIIntegration

_initialized = False

IN_APP_PACKAGES = ["voice_infra", "osce_assessment", "livekit_assessment_worker", "livekit_assistant_worker", "hosting"]


def _dsn() -> str:
    return os.getenv("SENTRY_DSN", "").strip().strip('"').strip("'")


def _environment() -> str:
    value = os.getenv("SENTRY_ENVIRONMENT", "").strip()
    if value:
        return value
    if (os.getenv("OSCE_LIVEKIT_HOSTING") or "").strip().lower() in {"cloud", "livekit-cloud"}:
        return "livekit-cloud"
    return "development"


def _release() -> str | None:
    return os.getenv("SENTRY_RELEASE", "").strip() or None


def _traces_sampler(sampling_context: dict[str, Any]) -> float:
    name = str(sampling_context.get("transaction_context", {}).get("name", ""))
    if "/health" in name or name in {"/", "health"}:
        return 0.0
    parent = sampling_context.get("parent_sampled")
    if parent is not None:
        return float(parent)
    return 0.2 if _environment() == "production" else 1.0


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    exc_info = hint.get("exc_info")
    if exc_info and issubclass(exc_info[0], (KeyboardInterrupt, SystemExit)):
        return None
    return event


def _reset_for_tests() -> None:
    global _initialized
    _initialized = False


def init_sentry(*, worker: str | None = None) -> bool:
    """Initialise once per process. No-op without SENTRY_DSN or under pytest."""
    global _initialized
    if _initialized:
        return True
    load_dotenv()
    if "pytest" in sys.modules and os.getenv("SENTRY_VERIFY_ERROR", "").strip() != "1":
        return False
    dsn = _dsn()
    if not dsn:
        return False
    sentry_sdk.init(
        dsn=dsn,
        environment=_environment(),
        release=_release(),
        send_default_pii=False,
        include_local_variables=False,
        traces_sampler=_traces_sampler,
        enable_logs=True,
        before_send=_before_send,
        in_app_include=IN_APP_PACKAGES,
        integrations=[AsyncioIntegration(), OpenAIIntegration(include_prompts=False), AnthropicIntegration(include_prompts=False)],
    )
    sentry_sdk.set_tag("livekit.worker", (worker or "").strip() or os.getenv("OSCE_LIVEKIT_WORKER", "").strip() or "unknown")
    _initialized = True
    return True


def raise_sentry_verify_error_if_requested() -> None:
    if os.getenv("SENTRY_VERIFY_ERROR", "").strip() != "1":
        return
    marker = os.getenv("SENTRY_VERIFY_MARKER", "").strip() or "livekit-setup"
    raise RuntimeError(f"Sentry test error {marker}")
