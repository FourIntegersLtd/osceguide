"""The one model call the CV slice makes: which model, and how it is asked."""

from __future__ import annotations

import openai
import pytest

from app.core.settings import Settings
from app.features.cv import llm
from app.features.cv.schemas import StructuredCv


async def test_the_cv_is_read_by_gpt_6_luna_with_reasoning_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """gpt-4o-mini retires on 2027-01-14; a reasoning model must be told to skip reasoning."""
    sent: dict[str, object] = {}
    cv = StructuredCv(summary="Foundation doctor")

    class _Completions:
        async def parse(self, **kwargs: object) -> object:
            sent.update(kwargs)
            message = type("Message", (), {"parsed": cv, "refusal": None})()
            return type("Response", (), {"choices": [type("Choice", (), {"message": message})()]})()

    class _Client:
        def __init__(self, **_: object) -> None:
            self.beta = type("Beta", (), {"chat": type("Chat", (), {"completions": _Completions()})()})()

    monkeypatch.setattr(openai, "AsyncOpenAI", _Client)

    settings = Settings(openai_api_key="sk-test")
    parsed, error = await llm.extract_structured("Foundation doctor", settings=settings)

    assert (parsed, error) == (cv, "")
    assert sent["model"] == llm.CV_MODEL
    assert sent["reasoning_effort"] == "none"
    assert sent["response_format"] is StructuredCv
    assert "temperature" not in sent and "max_tokens" not in sent
