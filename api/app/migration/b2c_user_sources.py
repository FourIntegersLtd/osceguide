"""Read-only sources for B2C user documents (Firestore or JSON export).

Writes go only to platform Postgres via `load_users`. Nothing here mutates
the legacy collections.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

B2C_USER_COLLECTIONS: dict[str, str] = {
    "sca": "users",
    "plab": "plab_users",
    "casc": "casc_users",
    "ortho": "ortho_users",
}


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


def _doc_to_dict(doc_id: str, data: dict[str, Any], *, app_type: str) -> dict[str, Any]:
    out = _serialize_value(dict(data))
    out["id"] = doc_id
    out.setdefault("app_type", app_type)
    return out


def read_users_json(path: Path) -> list[dict[str, Any]]:
    """Read `users.json` — array of documents, each with `app_type` when merged."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} should hold a JSON array of documents.")
    return data


def read_users_from_export_dir(export_dir: Path) -> list[dict[str, Any]]:
    return read_users_json(export_dir / "users.json")


def stream_b2c_user_documents(
    *,
    products: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Stream user documents from the four consumer collections (read-only)."""
    try:
        from google.cloud import firestore  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "google-cloud-firestore is not installed. "
            "Install the dev dependency: poetry install --with dev"
        ) from exc

    selected = list(products) if products is not None else list(B2C_USER_COLLECTIONS)
    unknown = [p for p in selected if p not in B2C_USER_COLLECTIONS]
    if unknown:
        raise ValueError(f"unknown product(s): {unknown}; expected {sorted(B2C_USER_COLLECTIONS)}")

    db = firestore.Client()
    out: list[dict[str, Any]] = []
    for app_type in selected:
        collection = B2C_USER_COLLECTIONS[app_type]
        for snap in db.collection(collection).stream():
            data = snap.to_dict() or {}
            out.append(_doc_to_dict(snap.id, data, app_type=app_type))
    return out


def write_users_json(path: Path, documents: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(documents, indent=2, ensure_ascii=False), encoding="utf-8")


def export_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
