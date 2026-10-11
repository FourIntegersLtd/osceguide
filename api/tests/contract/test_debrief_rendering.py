"""A debrief speaks first as the tutor and reviews the actual consultation."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.attempts import errors
from app.features.attempts import service_render as rendering

SEED = json.loads((Path(__file__).resolve().parents[2] / "seeds/platform-starter.json").read_text())
SCA_STRUCTURE = next(entry["rubric"]["structure"] for entry in SEED["exams"] if entry["code"] == "sca")
# An SCA mark as the engine stores it: a rating with evidence, missed items, a flag and an action.
SCA_RESULT = {
    "global_skills": {
        "structures_consultation": {"score": "A", "supporting_phrase": "Explored the patient's concerns."},
    },
    "clinical_analysis": {
        "missed_history": ["Pack-year smoking history"],
        "safety_considerations": ["Haemoptysis not asked about"],
    },
    "actionable_feedback": {
        "overall_priorities": ["Signpost before examining"],
        # Keys a mark stored before SCA stopped asking for them (its frozen rubric still had them).
        "tasks_feedback": {"improvements": ["Repeated tasks note"]},
        "language_adaptations": ["Generic language note"],
    },
}


@pytest.mark.asyncio
async def test_tutor_gets_source_transcript_marking_and_opening_line(monkeypatch):
    user_id, source_id = uuid4(), uuid4()
    source = SimpleNamespace(
        id=source_id,
        user_id=user_id,
        definition={
            "scenario": {"examiner_context": "Discuss smoking cessation."},
            # Frozen at render: the tutor reads the mark by this rubric's field roles.
            "evaluation_policy": {"rubric": {"structure": SCA_STRUCTURE}},
        },
    )
    monkeypatch.setattr(rendering.repository, "attempt_by_id", AsyncMock(return_value=source))
    monkeypatch.setattr(
        rendering.repository_transcript,
        "chunks_for",
        AsyncMock(
            return_value=[
                SimpleNamespace(role="user", message="What worries you most?"),
                SimpleNamespace(role="assistant", message="I am worried about my cough."),
            ]
        ),
    )
    monkeypatch.setattr(
        rendering.repository_transcript,
        "results_for",
        AsyncMock(
            return_value=[
                SimpleNamespace(payload=SCA_RESULT),
            ]
        ),
    )
    rendered = await rendering.render_debrief(
        None,
        SimpleNamespace(source_attempt_id=source_id, user_id=user_id),
        examiner_context="Edited later",
    )
    text = rendered["instructions"]
    assert "the tutor" in text
    assert "What worries you most?" in text
    assert "I am worried about my cough." in text
    assert "Discuss smoking cessation." in text
    # The mark, walked by role: the rating, its evidence, missed items, a flag and an action.
    assert "<marking>" in text
    for expected in (
        "Explored the patient's concerns.",
        "Pack-year smoking history",
        "Haemoptysis not asked about",
        "Signpost before examining",
        # An older mark still renders whole: the walk is over the stored payload.
        "Repeated tasks note",
        "Generic language note",
    ):
        assert expected in text
    assert "Edited later" not in text
    assert "How do you think it went?" in rendered["greeting"]
    # The ten-minute clock the prompt promises travels with it, for the worker to run.
    assert "This debrief is about 10 min long." in text
    assert rendered["tools"] == ["check_time"]
    pacing = rendered["tool_context"]["pacing"]
    assert pacing["total_seconds"] == 600
    assert [mark["at_seconds"] for mark in pacing["marks"]] == [150, 300, 480, 600]


@pytest.mark.asyncio
async def test_missing_source_cannot_be_debriefed(monkeypatch):
    monkeypatch.setattr(rendering.repository, "attempt_by_id", AsyncMock(return_value=None))
    with pytest.raises(errors.AttemptNotReady):
        await rendering.render_debrief(
            None,
            SimpleNamespace(source_attempt_id=uuid4(), user_id=uuid4()),
            examiner_context=None,
        )
