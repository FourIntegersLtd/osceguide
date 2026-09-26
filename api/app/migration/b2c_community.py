"""Transforms for B2C community → platform `posts` and `post_likes`."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.migration.legacy_ids import legacy_row_id
from app.migration.users import UnknownLegacyProduct, exam_for_product, parse_timestamp


class CommunityTransformError(Exception):
    pass


@dataclass(frozen=True)
class MigratedLike:

    legacy_ref: str
    post_legacy_ref: str
    legacy_user_id: str


@dataclass
class MigratedCommunityPost:

    legacy_ref: str
    kind: str
    exam_code: str
    author_legacy_user_id: str
    body: str
    title: str | None = None
    parent_legacy_ref: str | None = None
    legacy_station_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    likes: list[MigratedLike] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def row_id(self):
        return legacy_row_id(self.legacy_ref)

    @property
    def parent_row_id(self):
        if self.parent_legacy_ref is None:
            return None
        return legacy_row_id(self.parent_legacy_ref)


def _exam(document: dict[str, Any]) -> str:
    product = str(document.get("app_type") or "").strip().lower()
    if not product:
        raise CommunityTransformError("document has no app_type")
    return exam_for_product(product)


def _body_text(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        raise CommunityTransformError("empty body")
    return text


def _likes_for_post(
    *,
    exam_code: str,
    post_legacy_ref: str,
    liked_by: Any,
) -> list[MigratedLike]:
    if not isinstance(liked_by, list):
        return []
    likes: list[MigratedLike] = []
    for raw_user_id in liked_by:
        legacy_user = str(raw_user_id or "").strip()
        if not legacy_user:
            continue
        like_ref = f"{post_legacy_ref}:like:{legacy_user}"
        likes.append(
            MigratedLike(
                legacy_ref=like_ref,
                post_legacy_ref=post_legacy_ref,
                legacy_user_id=legacy_user,
            )
        )
    return likes


def question_from_document(document: dict[str, Any]) -> MigratedCommunityPost:
    try:
        exam_code = _exam(document)
    except UnknownLegacyProduct as exc:
        raise CommunityTransformError(str(exc)) from exc

    question_id = str(document.get("question_id") or document.get("id") or "").strip()
    if not question_id:
        raise CommunityTransformError("question has no question_id")

    user_id = str(document.get("user_id") or "").strip()
    if not user_id:
        raise CommunityTransformError(f"question {question_id} has no user_id")

    legacy_ref = f"{exam_code}:community:question:{question_id}"
    body = _body_text(document.get("content"))
    created = parse_timestamp(document.get("created_at"))
    updated = parse_timestamp(document.get("updated_at")) or created

    return MigratedCommunityPost(
        legacy_ref=legacy_ref,
        kind="question",
        exam_code=exam_code,
        author_legacy_user_id=user_id,
        body=body,
        title=None,
        created_at=created,
        updated_at=updated,
        likes=_likes_for_post(
            exam_code=exam_code,
            post_legacy_ref=legacy_ref,
            liked_by=document.get("liked_by"),
        ),
    )


def reply_from_document(document: dict[str, Any]) -> MigratedCommunityPost:
    try:
        exam_code = _exam(document)
    except UnknownLegacyProduct as exc:
        raise CommunityTransformError(str(exc)) from exc

    reply_id = str(document.get("reply_id") or document.get("id") or "").strip()
    question_id = str(document.get("question_id") or "").strip()
    if not reply_id:
        raise CommunityTransformError("reply has no reply_id")
    if not question_id:
        raise CommunityTransformError(f"reply {reply_id} has no question_id")

    user_id = str(document.get("user_id") or "").strip()
    if not user_id:
        raise CommunityTransformError(f"reply {reply_id} has no user_id")

    legacy_ref = f"{exam_code}:community:reply:{reply_id}"
    parent_legacy_ref = f"{exam_code}:community:question:{question_id}"
    body = _body_text(document.get("content"))
    created = parse_timestamp(document.get("created_at"))
    updated = parse_timestamp(document.get("updated_at")) or created

    return MigratedCommunityPost(
        legacy_ref=legacy_ref,
        kind="reply",
        exam_code=exam_code,
        author_legacy_user_id=user_id,
        body=body,
        parent_legacy_ref=parent_legacy_ref,
        created_at=created,
        updated_at=updated,
        likes=_likes_for_post(
            exam_code=exam_code,
            post_legacy_ref=legacy_ref,
            liked_by=document.get("liked_by"),
        ),
    )


def comment_from_document(document: dict[str, Any]) -> MigratedCommunityPost:
    try:
        exam_code = _exam(document)
    except UnknownLegacyProduct as exc:
        raise CommunityTransformError(str(exc)) from exc

    comment_id = str(document.get("comment_id") or document.get("id") or "").strip()
    station_id = str(document.get("station_id") or "").strip()
    if not comment_id:
        raise CommunityTransformError("comment has no comment_id")
    if not station_id:
        raise CommunityTransformError(f"comment {comment_id} has no station_id")

    user_id = str(document.get("user_id") or "").strip()
    if not user_id:
        raise CommunityTransformError(f"comment {comment_id} has no user_id")

    legacy_ref = f"{exam_code}:community:comment:{comment_id}"
    body = _body_text(document.get("comment"))
    created = parse_timestamp(document.get("created_at"))
    updated = parse_timestamp(document.get("updated_at")) or created

    warnings: list[str] = []
    moderation = document.get("moderation") or {}
    if isinstance(moderation, dict) and moderation.get("is_flagged"):
        warnings.append(f"comment {comment_id} was flagged in Firestore")

    return MigratedCommunityPost(
        legacy_ref=legacy_ref,
        kind="comment",
        exam_code=exam_code,
        author_legacy_user_id=user_id,
        body=body,
        legacy_station_id=station_id,
        created_at=created,
        updated_at=updated,
        likes=_likes_for_post(
            exam_code=exam_code,
            post_legacy_ref=legacy_ref,
            liked_by=document.get("liked_by"),
        ),
        warnings=warnings,
    )


def community_from_document(document: dict[str, Any]) -> MigratedCommunityPost:
    kind = str(document.get("_social_kind") or "").strip().lower()
    if kind == "question":
        return question_from_document(document)
    if kind == "reply":
        return reply_from_document(document)
    if kind == "comment":
        return comment_from_document(document)
    raise CommunityTransformError(f"unknown _social_kind {kind!r}")
