"""End-to-end tests against a real LiveKit server. Skipped unless configured.

Required environment:
    LIVEKIT_E2E_URL, LIVEKIT_E2E_KEY, LIVEKIT_E2E_SECRET   the LiveKit project
    LIVEKIT_E2E_AUDIO_WAV   a 16 kHz mono PCM WAV of a spoken sentence (the candidate's turn)
    DEEPGRAM_API_KEY, OPENAI_API_KEY (and any TTS keys the speech stack needs)

Run:  poetry run pytest -m e2e tests/e2e -q
"""

from __future__ import annotations

import os

import pytest

REQUIRED = ("LIVEKIT_E2E_URL", "LIVEKIT_E2E_KEY", "LIVEKIT_E2E_SECRET", "LIVEKIT_E2E_AUDIO_WAV", "DEEPGRAM_API_KEY")


def pytest_collection_modifyitems(config, items):
    missing = [v for v in REQUIRED if not os.environ.get(v)]
    if not missing:
        return
    skip = pytest.mark.skip(reason=f"e2e needs {missing}")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def e2e_env() -> dict[str, str]:
    return {v: os.environ[v] for v in REQUIRED}
