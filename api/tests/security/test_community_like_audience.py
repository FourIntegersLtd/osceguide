"""SEC-020: a post outside the viewer's audience cannot be liked.

`question_detail` and `list_replies` hide such a post as not found; `set_like`
must do the same, or a like succeeding would confirm the post exists.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import Audience, Visibility
from app.features.community import errors, repository, service
from app.features.identity import repository as identity_repository
from app.features.tenancy import repository as tenancy_repository

pytestmark = pytest.mark.db


async def user(session: AsyncSession, email: str) -> uuid.UUID:
    return (await identity_repository.create_user(session, email=email, name=email, password_hash=None)).id


# `app` binds the viewer-audience lookup `set_like` consults, as create_app does in production.
async def test_a_post_addressed_to_another_org_cannot_be_liked(db_session: AsyncSession, app) -> None:  # type: ignore[no-untyped-def]
    org = await tenancy_repository.create_organization(db_session, slug="closed-org", name="Closed")
    author = await user(db_session, "in@example.com")
    outsider = await user(db_session, "out@example.com")
    post = await repository.create_post(
        db_session,
        kind="question",
        author_id=author,
        title="Members only",
        body="For this organisation.",
        audience=Audience(visibility=Visibility.ORGANISATION, org_id=org.id),
    )

    with pytest.raises(errors.PostNotFound):
        await service.set_like(db_session, post.id, user_id=outsider, liked=True)


async def test_a_public_post_can_still_be_liked(db_session: AsyncSession, app) -> None:  # type: ignore[no-untyped-def]
    author = await user(db_session, "a@example.com")
    reader = await user(db_session, "r@example.com")
    post = await repository.create_post(
        db_session, kind="question", author_id=author, title="Open", body="Anyone.", audience=Audience()
    )

    liked = await service.set_like(db_session, post.id, user_id=reader, liked=True)
    assert liked.like_count == 1
