"""A debrief speaks first as the tutor and reviews the actual consultation."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.attempts import errors
from app.features.attempts import service_render as rendering


@pytest.mark.asyncio
async def test_tutor_gets_source_transcript_marking_and_opening_line(monkeypatch):
    user_id, source_id = uuid4(), uuid4()
    source = SimpleNamespace(
        id=source_id,
        user_id=user_id,
        definition={
            "scenario": {"examiner_context": "Discuss smoking cessation."},
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
                SimpleNamespace(payload={"feedback": "Explored the patient's concerns."}),
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
    assert "Explored the patient's concerns." in text
    assert "Edited later" not in text
    assert "How do you think it went?" in rendered["greeting"]


@pytest.mark.asyncio
async def test_missing_source_cannot_be_debriefed(monkeypatch):
    monkeypatch.setattr(rendering.repository, "attempt_by_id", AsyncMock(return_value=None))
    with pytest.raises(errors.AttemptNotReady):
        await rendering.render_debrief(
            None,
            SimpleNamespace(source_attempt_id=uuid4(), user_id=uuid4()),
            examiner_context=None,
        )
