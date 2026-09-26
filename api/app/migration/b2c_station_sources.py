"""Read-only sources for the B2C station library (Firestore or JSON export).

Writes go only to platform Postgres via `load_stations`. Nothing here mutates
the legacy collections.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.migration import b2c_firestore

B2C_STATION_COLLECTIONS: dict[str, str] = {
    "sca": "stations",
    "plab": "plab_stations",
    "casc": "casc_stations",
    "ortho": "ortho_stations",
}


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


def _doc_to_dict(doc_id: str, document_data: dict[str, Any], *, app_type: str) -> dict[str, Any]:
    """A Firestore station snapshot as a plain dict, with its id and product tagged on."""
    document = _serialize_value(dict(document_data))
    document["id"] = doc_id
    document.setdefault("app_type", app_type)
    return document


def read_stations_json(path: Path) -> list[dict[str, Any]]:
    """Read `stations.json` — array of documents, each with `app_type` when merged."""
    documents = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(documents, list):
        raise ValueError(f"{path} should hold a JSON array of documents.")
    return documents


def read_stations_from_export_dir(export_dir: Path) -> list[dict[str, Any]]:
    """Read `stations.json` from a directory produced by an earlier export run."""
    return read_stations_json(export_dir / "stations.json")


def stream_b2c_station_documents(
    *,
    products: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Stream all station documents from the four consumer collections (read-only)."""
    selected = list(products) if products is not None else list(B2C_STATION_COLLECTIONS)
    unknown = [product for product in selected if product not in B2C_STATION_COLLECTIONS]
    if unknown:
        raise ValueError(f"unknown product(s): {unknown}; expected {sorted(B2C_STATION_COLLECTIONS)}")

    db = b2c_firestore.client()
    documents: list[dict[str, Any]] = []
    for app_type in selected:
        collection = B2C_STATION_COLLECTIONS[app_type]
        for snapshot in db.collection(collection).stream():
            document_data = snapshot.to_dict() or {}
            documents.append(_doc_to_dict(snapshot.id, document_data, app_type=app_type))
    return documents


def write_stations_json(path: Path, documents: list[dict[str, Any]]) -> None:
    """Write an export of station documents to `path` as a JSON array, creating parent folders."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(documents, indent=2, ensure_ascii=False), encoding="utf-8")


def export_timestamp() -> str:
    """The current UTC time as a Zulu-suffixed ISO string, for naming an export."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
