"""The mode table is the only place the assistant worker decides anything per session type."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from livekit_assistant_worker.modes import MODE_PROFILES, WorkerType, is_faq_help, mode_profile

PACKAGE = Path(__file__).resolve().parents[1] / "packages" / "livekit_assistant_worker"
TYPE_LITERALS = re.compile(r"^(help|onboarding|dashboard|consulting-doctor)$")
# Modules allowed to spell a session type as a string: the table itself, and templates that are per type by nature.
ALLOWED = {"modes.py"}


def test_every_worker_type_has_a_profile() -> None:
    assert set(MODE_PROFILES) == set(WorkerType)
    for worker_type, profile in MODE_PROFILES.items():
        assert profile.worker_type is worker_type
        assert mode_profile(worker_type.value) is profile


def test_data_driven_modes_run_no_screen_tools_and_only_the_dashboard_delivers_its_turns() -> None:
    """The consulting doctor keeps nothing; the dashboard hands its turns to the backend, which summarises."""
    for worker_type in (WorkerType.DASHBOARD, WorkerType.CONSULTING_DOCTOR):
        profile = mode_profile(worker_type)
        assert not profile.ui_guidance and not profile.gpt_live_eligible and not profile.scene_updates
    assert not mode_profile(WorkerType.CONSULTING_DOCTOR).keeps_transcript
    assert mode_profile(WorkerType.DASHBOARD).keeps_transcript and mode_profile(WorkerType.DASHBOARD).llm == "tutor"
    assert mode_profile(WorkerType.HELP).keeps_transcript and mode_profile(WorkerType.HELP).ui_guidance
    assert mode_profile(WorkerType.ONBOARDING).opens_with_generated_reply and mode_profile(WorkerType.ONBOARDING).scene_updates


def test_only_the_dashboard_loads_the_backends_tools() -> None:
    assert mode_profile(WorkerType.DASHBOARD).remote_tools
    for worker_type in (WorkerType.HELP, WorkerType.ONBOARDING, WorkerType.CONSULTING_DOCTOR):
        assert not mode_profile(worker_type).remote_tools


def test_only_the_consulting_doctor_runs_against_a_clock() -> None:
    """The one interaction with a station length to keep to; the rest end when the user leaves."""
    assert mode_profile(WorkerType.CONSULTING_DOCTOR).paced
    for worker_type in (WorkerType.HELP, WorkerType.ONBOARDING, WorkerType.DASHBOARD):
        assert not mode_profile(worker_type).paced


def test_the_worker_holds_no_session_prompt_or_faq_content() -> None:
    names = {p.name for p in PACKAGE.rglob("*.py")}
    assert not names & {"faq.py", "help.py", "onboarding.py", "gpt_live.py"}


def test_unknown_types_are_refused() -> None:
    with pytest.raises(ValueError):
        mode_profile("conversation")


def test_faq_help_is_the_only_speech_to_speech_shape() -> None:
    assert is_faq_help("help", "faq") and not is_faq_help("help", "guide") and not is_faq_help("onboarding", "faq")


def test_no_module_outside_the_table_compares_session_types_as_strings() -> None:
    offenders = []
    for path in PACKAGE.rglob("*.py"):
        if path.name in ALLOWED or path.parts[-2] in ("prompts", "ui_guidance"):
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Compare):
                for side in (node.left, *node.comparators):
                    if isinstance(side, ast.Constant) and isinstance(side.value, str) and TYPE_LITERALS.match(side.value):
                        offenders.append(f"{path.name}:{node.lineno} {side.value!r}")
    assert offenders == []
