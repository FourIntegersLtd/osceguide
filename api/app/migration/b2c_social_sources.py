"""Read-only sources for B2C community and marketplace (Firestore or JSON export)."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

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
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:  # noqa: BLE001
            return str(value)
    if isinstance(value, dict):
        return {str(k): _serialize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize_value(v) for v in value]
    return value


def _doc_to_dict(
    doc_id: str,
    data: dict[str, Any],
    *,
    app_type: str,
    social_kind: str,
) -> dict[str, Any]:
    out = _serialize_value(dict(data))
    out["id"] = doc_id
    out.setdefault("app_type", app_type)
    out["_social_kind"] = social_kind
    return out


def read_community_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} should hold a JSON array of documents.")
    return data


def read_marketplace_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} should hold a JSON array of documents.")
    return data


def read_community_from_export_dir(export_dir: Path) -> list[dict[str, Any]]:
    return read_community_json(export_dir / "community.json")


def read_marketplace_from_export_dir(export_dir: Path) -> list[dict[str, Any]]:
    return read_marketplace_json(export_dir / "marketplace.json")


def _stream_collection(
    db: Any,
    collection: str,
    *,
    app_type: str,
    social_kind: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for snap in db.collection(collection).stream():
        data = snap.to_dict() or {}
        out.append(_doc_to_dict(snap.id, data, app_type=app_type, social_kind=social_kind))
    return out


def stream_b2c_community_documents(
    *,
    kinds: Iterable[CommunityDocKind] | None = None,
    products: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    try:
        from google.cloud import firestore  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "google-cloud-firestore is not installed. Install the dev dependency: poetry install --with dev"
        ) from exc

    selected_kinds = list(kinds) if kinds is not None else ["question", "reply", "comment"]
    selected_products = list(products) if products is not None else list(ALL_EXAMS)
    for product in selected_products:
        if product not in ALL_EXAMS:
            raise ValueError(f"unknown product {product!r}")

    db = firestore.Client()
    out: list[dict[str, Any]] = []
    for app_type in selected_products:
        if "question" in selected_kinds:
            out.extend(
                _stream_collection(
                    db,
                    B2C_COMMUNITY_QUESTION_COLLECTIONS[app_type],
                    app_type=app_type,
                    social_kind="question",
                )
            )
        if "reply" in selected_kinds:
            out.extend(
                _stream_collection(
                    db,
                    B2C_COMMUNITY_REPLY_COLLECTIONS[app_type],
                    app_type=app_type,
                    social_kind="reply",
                )
            )
        if "comment" in selected_kinds:
            out.extend(
                _stream_collection(
                    db,
                    B2C_COMMENT_COLLECTIONS[app_type],
                    app_type=app_type,
                    social_kind="comment",
                )
            )
    return out


def stream_b2c_marketplace_documents(
    *,
    kinds: Iterable[MarketplaceDocKind] | None = None,
    products: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    try:
        from google.cloud import firestore  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "google-cloud-firestore is not installed. Install the dev dependency: poetry install --with dev"
        ) from exc

    selected_kinds = list(kinds) if kinds is not None else ["post", "session"]
    selected_products = list(products) if products is not None else list(ALL_EXAMS)
    for product in selected_products:
        if product not in ALL_EXAMS:
            raise ValueError(f"unknown product {product!r}")

    db = firestore.Client()
    out: list[dict[str, Any]] = []
    for app_type in selected_products:
        if "post" in selected_kinds:
            out.extend(
                _stream_collection(
                    db,
                    B2C_MARKETPLACE_POST_COLLECTIONS[app_type],
                    app_type=app_type,
                    social_kind="post",
                )
            )
        if "session" in selected_kinds:
            out.extend(
                _stream_collection(
                    db,
                    B2C_MARKETPLACE_SESSION_COLLECTIONS[app_type],
                    app_type=app_type,
                    social_kind="session",
                )
            )
    return out


def write_community_json(path: Path, documents: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(documents, indent=2, ensure_ascii=False), encoding="utf-8")


def write_marketplace_json(path: Path, documents: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(documents, indent=2, ensure_ascii=False), encoding="utf-8")


def export_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
