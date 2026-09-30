"""Study trials unlock only the account exam, for fourteen days."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.media import service_search


@pytest.mark.asyncio
@pytest.mark.parametrize("age,allowed", [(0, True), (13, True), (14, False), (15, False)])
async def test_study_trial_window_and_exam_scope(monkeypatch, age, allowed):
    now = datetime(2026, 9, 20, tzinfo=UTC)
    sca_id, plab_id = uuid4(), uuid4()
    monkeypatch.setattr(service_search.entitlements, "list_for_user", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        service_search.identity,
        "user_ref_by_id",
        AsyncMock(
            return_value=SimpleNamespace(
                exam_code="sca",
                created_at=now - timedelta(days=age),
            )
        ),
    )
    monkeypatch.setattr(
        service_search.catalog,
        "exam_refs",
        AsyncMock(
            return_value=[
                SimpleNamespace(id=sca_id, code="sca"),
                SimpleNamespace(id=plab_id, code="plab"),
            ]
        ),
    )
    result = await service_search.unlocked_exam_ids(None, uuid4(), now=now)
    assert result == (frozenset({sca_id}) if allowed else frozenset())


@pytest.mark.asyncio
async def test_paid_access_survives_expired_trial(monkeypatch):
    now = datetime(2026, 9, 20, tzinfo=UTC)
    paid_id, revoked_id = uuid4(), uuid4()
    monkeypatch.setattr(
        service_search.entitlements,
        "list_for_user",
        AsyncMock(
            return_value=[
                SimpleNamespace(exam_id=paid_id, live=True),
                SimpleNamespace(exam_id=revoked_id, live=False),
            ]
        ),
    )
    monkeypatch.setattr(
        service_search.identity,
        "user_ref_by_id",
        AsyncMock(
            return_value=SimpleNamespace(
                exam_code="sca",
                created_at=now - timedelta(days=30),
            )
        ),
    )
    assert await service_search.unlocked_exam_ids(None, uuid4(), now=now) == frozenset({paid_id})


@pytest.mark.asyncio
async def test_signed_out_reader_has_no_trial():
    assert await service_search.unlocked_exam_ids(None, None, now=datetime.now(UTC)) == frozenset()
