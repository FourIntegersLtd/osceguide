"""Read-only sources for B2C community and marketplace (Firestore or JSON export)."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from app.migration import b2c_firestore

CommunityDocKind = Literal["question", "reply", "comment"]
MarketplaceDocKind = Literal["post", "session"]

B2C_COMMUNITY_QUESTION_COLLECTIONS: dict[str, str] = {
    "sca": "community_questions",
    "plab": "plab_community_questions",
    "casc": "casc_community_questions",
    "ortho": "ortho_community_questions",
}

B2C_COMMUNITY_REPLY_COLLECTIONS: dict[str, str] = {
    "sca": "community_replies",
    "plab": "plab_community_replies",
    "casc": "casc_community_replies",
    "ortho": "ortho_community_replies",
}

B2C_COMMENT_COLLECTIONS: dict[str, str] = {
    "sca": "comments",
    "plab": "plab_comments",
    "casc": "casc_comments",
    "ortho": "ortho_comments",
}

B2C_MARKETPLACE_POST_COLLECTIONS: dict[str, str] = {
    "sca": "marketplace_posts",
    "plab": "plab_marketplace_posts",
    "casc": "casc_marketplace_posts",
    "ortho": "ortho_marketplace_posts",
}

B2C_MARKETPLACE_SESSION_COLLECTIONS: dict[str, str] = {
    "sca": "marketplace_sessions",
    "plab": "plab_marketplace_sessions",
    "casc": "casc_marketplace_sessions",
    "ortho": "ortho_marketplace_sessions",
}

ALL_EXAMS: tuple[str, ...] = ("sca", "plab", "casc", "ortho")


def _serialize_value(value: Any) -> Any:
    """Recursively turn a Firestore value (including nested dicts/lists) into a JSON-safe one."""
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:  # noqa: BLE001
            return str(value)
    if isinstance(value, dict):
        return {str(key): _serialize_value(nested_value) for key, nested_value in value.items()}
    if isinstance(value, list):
        return [_serialize_value(nested_value) for nested_value in value]
    return value


def _doc_to_dict(
    doc_id: str,
    document_data: dict[str, Any],
    *,
    app_type: str,
    social_kind: str,
) -> dict[str, Any]:
    """A Firestore community/marketplace snapshot as a plain dict, with its id, product and kind tagged on."""
    document = _serialize_value(dict(document_data))
    document["id"] = doc_id
    document.setdefault("app_type", app_type)
    document["_social_kind"] = social_kind
    return document


def read_community_json(path: Path) -> list[dict[str, Any]]:
    """Read a community export file — array of question/reply/comment documents."""
    documents = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(documents, list):
        raise ValueError(f"{path} should hold a JSON array of documents.")
    return documents


def read_marketplace_json(path: Path) -> list[dict[str, Any]]:
    """Read a marketplace export file — array of post/session documents."""
    documents = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(documents, list):
        raise ValueError(f"{path} should hold a JSON array of documents.")
    return documents


def read_community_from_export_dir(export_dir: Path) -> list[dict[str, Any]]:
    """Read `community.json` from a directory produced by an earlier export run."""
    return read_community_json(export_dir / "community.json")


def read_marketplace_from_export_dir(export_dir: Path) -> list[dict[str, Any]]:
    """Read `marketplace.json` from a directory produced by an earlier export run."""
    return read_marketplace_json(export_dir / "marketplace.json")


def _stream_collection(
    db: Any,
    collection: str,
    *,
    app_type: str,
    social_kind: str,
) -> list[dict[str, Any]]:
    """Every document in one Firestore collection, tagged with its product and social kind."""
    documents: list[dict[str, Any]] = []
    for snapshot in db.collection(collection).stream():
        document_data = snapshot.to_dict() or {}
        documents.append(_doc_to_dict(snapshot.id, document_data, app_type=app_type, social_kind=social_kind))
    return documents


def stream_b2c_community_documents(
    *,
    kinds: Iterable[CommunityDocKind] | None = None,
    products: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Stream community question/reply/comment documents from consumer Firestore (read-only)."""
    selected_kinds = list(kinds) if kinds is not None else ["question", "reply", "comment"]
    selected_products = list(products) if products is not None else list(ALL_EXAMS)
    for product in selected_products:
        if product not in ALL_EXAMS:
            raise ValueError(f"unknown product {product!r}")

    db = b2c_firestore.client()
    documents: list[dict[str, Any]] = []
    for app_type in selected_products:
        if "question" in selected_kinds:
            documents.extend(
                _stream_collection(
                    db,
                    B2C_COMMUNITY_QUESTION_COLLECTIONS[app_type],
                    app_type=app_type,
                    social_kind="question",
                )
            )
        if "reply" in selected_kinds:
            documents.extend(
                _stream_collection(
                    db,
                    B2C_COMMUNITY_REPLY_COLLECTIONS[app_type],
                    app_type=app_type,
                    social_kind="reply",
                )
            )
        if "comment" in selected_kinds:
            documents.extend(
                _stream_collection(
                    db,
                    B2C_COMMENT_COLLECTIONS[app_type],
                    app_type=app_type,
                    social_kind="comment",
                )
            )
    return documents


def stream_b2c_marketplace_documents(
    *,
    kinds: Iterable[MarketplaceDocKind] | None = None,
    products: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Stream marketplace post/session documents from consumer Firestore (read-only)."""
    selected_kinds = list(kinds) if kinds is not None else ["post", "session"]
    selected_products = list(products) if products is not None else list(ALL_EXAMS)
    for product in selected_products:
        if product not in ALL_EXAMS:
            raise ValueError(f"unknown product {product!r}")

    db = b2c_firestore.client()
    documents: list[dict[str, Any]] = []
    for app_type in selected_products:
        if "post" in selected_kinds:
            documents.extend(
                _stream_collection(
                    db,
                    B2C_MARKETPLACE_POST_COLLECTIONS[app_type],
                    app_type=app_type,
                    social_kind="post",
                )
            )
        if "session" in selected_kinds:
            documents.extend(
                _stream_collection(
                    db,
                    B2C_MARKETPLACE_SESSION_COLLECTIONS[app_type],
                    app_type=app_type,
                    social_kind="session",
                )
            )
    return documents


def write_community_json(path: Path, documents: list[dict[str, Any]]) -> None:
    """Write an export of community documents to `path` as a JSON array, creating parent folders."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(documents, indent=2, ensure_ascii=False), encoding="utf-8")


def write_marketplace_json(path: Path, documents: list[dict[str, Any]]) -> None:
    """Write an export of marketplace documents to `path` as a JSON array, creating parent folders."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(documents, indent=2, ensure_ascii=False), encoding="utf-8")


def export_timestamp() -> str:
    """The current UTC time as a Zulu-suffixed ISO string, for naming an export."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
