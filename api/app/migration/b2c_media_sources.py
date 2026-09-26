"""Read-only sources for B2C study material (Firestore or JSON export).

Writes go only to platform Postgres via `load_media`. Nothing here mutates
the legacy collections.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

MediaKindSource = Literal["summary", "blog", "slide_deck"]

B2C_MEDIA_SUMMARY_COLLECTIONS: dict[str, str] = {
    "sca": "summaries",
    "plab": "plab_summaries",
    "casc": "casc_summaries",
    "ortho": "ortho_summaries",
}

B2C_MEDIA_BLOG_COLLECTIONS: dict[str, str] = {
    "sca": "blogs",
    "plab": "plab_blogs",
    "casc": "casc_blogs",
    "ortho": "ortho_blogs",
}

B2C_MEDIA_SLIDE_COLLECTIONS: dict[str, str] = {
    "sca": "slides",
    "plab": "plab_slides",
    "casc": "casc_slides",
    "ortho": "ortho_slides",
}

_MEDIA_KIND_TO_MAP: dict[MediaKindSource, dict[str, str]] = {
    "summary": B2C_MEDIA_SUMMARY_COLLECTIONS,
    "blog": B2C_MEDIA_BLOG_COLLECTIONS,
    "slide_deck": B2C_MEDIA_SLIDE_COLLECTIONS,
}

ALL_MEDIA_KINDS: tuple[MediaKindSource, ...] = ("summary", "blog", "slide_deck")


def _serialize_value(value: Any) -> Any:
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
    media_kind: MediaKindSource,
) -> dict[str, Any]:
    document = _serialize_value(dict(document_data))
    document["id"] = doc_id
    document.setdefault("app_type", app_type)
    document["_media_kind"] = media_kind
    return document


def read_media_json(path: Path) -> list[dict[str, Any]]:
    """Read `media.json` — array of documents, each with `app_type` and `_media_kind`."""
    documents = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(documents, list):
        raise ValueError(f"{path} should hold a JSON array of documents.")
    return documents


def read_media_from_export_dir(export_dir: Path) -> list[dict[str, Any]]:
    return read_media_json(export_dir / "media.json")


def stream_b2c_media_documents(
    *,
    kinds: Iterable[MediaKindSource] | None = None,
    products: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Stream study-material documents from consumer Firestore collections (read-only)."""
    try:
        from google.cloud import firestore  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "google-cloud-firestore is not installed. Install the dev dependency: poetry install --with dev"
        ) from exc

    selected_kinds = list(kinds) if kinds is not None else list(ALL_MEDIA_KINDS)
    unknown_kinds = [kind for kind in selected_kinds if kind not in _MEDIA_KIND_TO_MAP]
    if unknown_kinds:
        raise ValueError(f"unknown media kind(s): {unknown_kinds}; expected {ALL_MEDIA_KINDS}")

    reference_map = _MEDIA_KIND_TO_MAP[selected_kinds[0]]
    selected_products = list(products) if products is not None else list(reference_map)
    for kind in selected_kinds:
        kind_map = _MEDIA_KIND_TO_MAP[kind]
        unknown = [product for product in selected_products if product not in kind_map]
        if unknown:
            raise ValueError(f"unknown product(s) for {kind}: {unknown}")

    db = firestore.Client()
    documents: list[dict[str, Any]] = []
    for media_kind in selected_kinds:
        collections = _MEDIA_KIND_TO_MAP[media_kind]
        for app_type in selected_products:
            collection = collections[app_type]
            for snapshot in db.collection(collection).stream():
                document_data = snapshot.to_dict() or {}
                documents.append(
                    _doc_to_dict(snapshot.id, document_data, app_type=app_type, media_kind=media_kind)
                )
    return documents


def write_media_json(path: Path, documents: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(documents, indent=2, ensure_ascii=False), encoding="utf-8")


def export_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
