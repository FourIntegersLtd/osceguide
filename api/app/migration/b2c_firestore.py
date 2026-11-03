"""Read-only access to the consumer Firestore for the one-way copy.

Nothing here writes, updates or deletes: the only calls made are
`collections()` and `stream()`. Every document comes back as a plain dict with
its Firestore id under `id` and the product it belongs to under `app_type`, so
the transforms never see a Firestore type.

Documents tagged `_seed_tag` (or created by a `seed_*` actor) are demo rows the
partner dashboard was seeded with, not anybody's data, and are dropped here so
no step has to remember to.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from app.migration import bucket_moves


def configure_credentials_from_env() -> None:
    """Same credential sources as b2c-api: a key path, or the key JSON itself."""
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        key_path = (os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH") or "").strip()
        if key_path:
            resolved = Path(key_path).expanduser()
            if resolved.is_file():
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(resolved)

    json_content = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON") or os.getenv(
        "FIREBASE_SERVICE_ACCOUNT_KEY"
    )
    if not json_content or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return
    try:
        json.loads(json_content)
    except json.JSONDecodeError:
        return
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as handle:
        handle.write(json_content)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = handle.name


_override: Any = None


def use_client(replacement: Any) -> None:
    """Make every later `client()` call return `replacement` (the sync's pending-only wrapper)."""
    global _override  # noqa: PLW0603
    _override = replacement


def client() -> Any:
    """A Firestore client, credentialed from the environment. Read-only by convention.

    The only place this codebase opens Firestore; every source module asks here.
    """
    if _override is not None:
        return _override
    try:
        from google.cloud import firestore  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "google-cloud-firestore is not installed. Install the dev dependency: poetry install --with dev"
        ) from exc
    configure_credentials_from_env()
    return firestore.Client()


def serialize(value: Any) -> Any:
    """JSON-safe copy of a Firestore value. NUL characters are dropped: Postgres
    text and JSONB both refuse them, and a few legacy model outputs carry one.
    A link to a bucket file that has moved comes back pointing at its new place."""
    if isinstance(value, str):
        return bucket_moves.rewrite_links(value.replace("\x00", ""))
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:  # noqa: BLE001
            return str(value)
    if isinstance(value, dict):
        return {str(key): serialize(nested_value) for key, nested_value in value.items()}
    if isinstance(value, list):
        return [serialize(nested_value) for nested_value in value]
    return value


def is_seed(document: dict[str, Any]) -> bool:
    """Whether a document is partner-dashboard demo data rather than a real record."""
    if document.get("_seed_tag"):
        return True
    return any(str(document.get(key) or "").startswith("seed_") for key in ("created_by", "user_id"))


USER_COLLECTIONS = ("users", "plab_users", "casc_users", "ortho_users")


def deleted_user_ids(db: Any) -> set[str]:
    """Legacy ids of people who deleted their account. Their email is already
    scrubbed and their history is not copied."""
    deleted_ids: set[str] = set()
    for collection in USER_COLLECTIONS:
        for snapshot in db.collection(collection).select(["user_id", "is_deleted"]).stream():
            document_data = snapshot.to_dict() or {}
            if document_data.get("is_deleted") is True:
                deleted_ids.update({snapshot.id, str(document_data.get("user_id") or snapshot.id)})
    return deleted_ids


def root_collection_names(db: Any) -> list[str]:
    """Every top-level collection name that actually exists in this Firestore project."""
    return sorted(collection.id for collection in db.collections())


def stream(db: Any, collection: str, *, app_type: str | None = None) -> tuple[list[dict[str, Any]], int]:
    """Every non-seed document in `collection`, and how many seed rows were dropped."""
    documents: list[dict[str, Any]] = []
    seeded = 0
    for snapshot in db.collection(collection).stream():
        document = serialize(snapshot.to_dict() or {})
        if is_seed(document):
            seeded += 1
            continue
        document["id"] = snapshot.id
        if app_type is not None:
            document.setdefault("app_type", app_type)
        document["_collection"] = collection
        documents.append(document)
    return documents, seeded
