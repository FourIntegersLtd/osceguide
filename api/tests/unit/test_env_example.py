"""`.env.example` is the first thing a new engineer copies, so it has to be true.

It drifted badly once: its header still described a three-secret rule long
after ten values became required, and it listed none of `LIVEKIT_*`,
`OPENAI_API_KEY`, `STRIPE_WEBHOOK_SECRET` or `RESEND_API_KEY`. Someone
following it got a process that would not boot in staging and no clue why.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.core.settings import REQUIRED_WHEN_DEPLOYED, Settings

EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"
NAMED = {m.group(1) for m in re.finditer(r"^([A-Z][A-Z0-9_]*)=", EXAMPLE.read_text(), re.M)}


def test_every_name_in_the_example_is_a_real_setting() -> None:
    """A variable the app never reads is worse than none: it looks configured."""
    assert not NAMED - {name.upper() for name in Settings.model_fields}


def test_every_value_required_in_a_deployment_is_in_the_example() -> None:
    assert not set(REQUIRED_WHEN_DEPLOYED) - NAMED
