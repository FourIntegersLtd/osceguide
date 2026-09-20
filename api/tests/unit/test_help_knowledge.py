from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.assistant import service_knowledge as service
from app.features.assistant.schemas_help import KnowledgeChat


@pytest.mark.asyncio
@pytest.mark.parametrize("has_access,locked", [(False, False), (True, True), (True, False)])
async def test_answers_use_only_unlocked_exam_material(monkeypatch, has_access, locked):
    sca, plab = uuid4(), uuid4()
    monkeypatch.setattr(
        service.catalog,
        "exam_refs",
        AsyncMock(
            return_value=[
                SimpleNamespace(id=sca, code="sca"),
                SimpleNamespace(id=plab, code="plab"),
            ]
        ),
    )
    monkeypatch.setattr(
        service.service_search,
        "unlocked_exam_ids",
        AsyncMock(return_value=frozenset({sca, plab} if has_access else {plab})),
    )
    search = AsyncMock(return_value=[SimpleNamespace(slug="hypertension")])
    monkeypatch.setattr(service.service_search, "search", search)
    monkeypatch.setattr(
        service.media,
        "read_by_slug",
        AsyncMock(
            return_value=SimpleNamespace(
                locked=locked,
                content={"body": "A reference passage"},
                title="Hypertension",
                kind="summary",
                exam_code="sca",
            )
        ),
    )
    completion = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Grounded answer"))]
        )
    )
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=completion)))
    manager = AsyncMock()
    manager.__aenter__.return_value = client
    monkeypatch.setattr(service, "AsyncOpenAI", lambda **kwargs: manager)
    result = await service.answer(
        None,
        KnowledgeChat(messages=[{"role": "user", "content": "Hypertension?"}]),
        user_id=uuid4(),
        now=datetime.now(UTC),
        index=None,
        settings=SimpleNamespace(openai_api_key="test"),
    )
    if not has_access:
        search.assert_not_called()
        completion.assert_not_called()
    elif locked:
        completion.assert_not_called()
    else:
        assert result.reply == "Grounded answer"
        assert search.call_args.kwargs["unlocked"] == frozenset({sca})
        assert "A reference passage" in completion.call_args.kwargs["messages"][0]["content"]
