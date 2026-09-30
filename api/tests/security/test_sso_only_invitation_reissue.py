"""SEC-011: an SSO-only account is never re-sent a set-password link.

`confirm_password_reset` already refuses such an account; this is the first
line, so the token is never minted or emailed at all.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import repository, service_invitations

pytestmark = pytest.mark.db


async def test_an_sso_only_account_is_not_reissued_an_invitation(db_session: AsyncSession) -> None:
    user = await repository.create_user(
        db_session, email="sso@example.com", name="SSO", password_hash=None, password_login_disabled=True
    )
    sent = await service_invitations.reissue_invitation(
        db_session, user_id=user.id, invited_to="Kings", now=datetime.now(UTC)
    )
    assert sent is False


async def test_an_ordinary_invitee_is_still_reissued_one(db_session: AsyncSession) -> None:
    user = await repository.create_user(db_session, email="pw@example.com", name="PW", password_hash=None)
    sent = await service_invitations.reissue_invitation(
        db_session, user_id=user.id, invited_to="Kings", now=datetime.now(UTC)
    )
    assert sent is True
