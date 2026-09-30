"""End-to-end tests: the real assessment worker against this API. Skipped unless configured.

Required environment (same names as `assessment/tests/e2e`):
    LIVEKIT_E2E_URL, LIVEKIT_E2E_KEY, LIVEKIT_E2E_SECRET   the LiveKit project
    LIVEKIT_E2E_AUDIO_WAV   a 16 kHz mono PCM WAV of a spoken sentence (the candidate's turn)
    DEEPGRAM_API_KEY, OPENAI_API_KEY
    ASSESSMENT_PLATFORM_ROOT   checkout of assessment-platform, for the worker entrypoint and harness

Run:  poetry run pytest -m e2e tests/e2e -q

The tests themselves arrive with the attempts slice (Phase 3); this gate is
in place first so the marker and the skip reason are settled.
"""

from __future__ import annotations

import os

import pytest

REQUIRED = (
    "LIVEKIT_E2E_URL",
    "LIVEKIT_E2E_KEY",
    "LIVEKIT_E2E_SECRET",
    "LIVEKIT_E2E_AUDIO_WAV",
    "DEEPGRAM_API_KEY",
    "OPENAI_API_KEY",
    "ASSESSMENT_PLATFORM_ROOT",
)


def _configured(name: str) -> str:
    """An e2e setting, reading OpenAI's key from where `tests/conftest.py` set it aside."""
    if name == "OPENAI_API_KEY":
        return os.environ.get("OPENAI_API_KEY") or os.environ.get("E2E_OPENAI_API_KEY", "")
    return os.environ.get(name, "")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    missing = [v for v in REQUIRED if not _configured(v)]
    if not missing:
        return
    skip = pytest.mark.skip(reason=f"e2e needs {missing}")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def e2e_env() -> dict[str, str]:
    """The e2e settings, with OpenAI's key restored so the worker subprocess inherits it."""
    os.environ["OPENAI_API_KEY"] = _configured("OPENAI_API_KEY")
    return {v: _configured(v) for v in REQUIRED}
