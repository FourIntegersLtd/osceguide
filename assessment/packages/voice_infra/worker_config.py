"""Environment-backed worker configuration shared by all hosting targets."""

from __future__ import annotations

import os


def optional_agent_name(variable: str) -> str | None:
    return os.getenv(variable, "").strip() or None


def required_agent_name(variable: str) -> str:
    value = optional_agent_name(variable)
    if value is None:
        raise RuntimeError(f"{variable} must be set to a named dispatch agent")
    return value


def required_choice(variable: str, choices: tuple[str, ...]) -> str:
    value = os.getenv(variable, "").strip().lower()
    if value not in choices:
        raise RuntimeError(f"{variable} must be one of {', '.join(repr(c) for c in choices)}")
    return value


def worker_port(variable: str, default: int) -> int:
    raw = os.getenv(variable, str(default)).strip()
    try:
        port = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{variable} must be an integer") from exc
    if not 1 <= port <= 65535:
        raise RuntimeError(f"{variable} must be between 1 and 65535")
    return port


def required_deepgram_api_key() -> str:
    value = (os.getenv("DEEPGRAM_API_KEY") or "").strip()
    if not value:
        raise RuntimeError("DEEPGRAM_API_KEY must be set for direct Deepgram STT/TTS")
    return value


def optional_max_concurrent_jobs(variable: str, *, default: int | None = None) -> int | None:
    """Unset uses ``default``. ``0``/``off``/``disabled`` disables the cap."""
    raw = os.getenv(variable, "").strip().lower()
    if not raw:
        return default
    if raw in {"0", "off", "false", "no", "disabled", "none"}:
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{variable} must be a positive integer") from exc
    return value if value >= 1 else None


def optional_load_threshold(variable: str, *, default: float = 0.99) -> float:
    """A production load threshold in (0, 1). Dev mode uses math.inf separately."""
    raw = os.getenv(variable, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{variable} must be a number between 0 and 1") from exc
    if not 0 < value < 1:
        raise RuntimeError(f"{variable} must be between 0 and 1 (exclusive)")
    return value


def optional_float(variable: str, default: float) -> float:
    """``default`` when unset or unparsable; workers use it for tunable timeouts."""
    raw = (os.getenv(variable) or "").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        return default
