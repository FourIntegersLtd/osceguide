"""Cursor pagination.

Every list endpoint returns `Page[T]`: the items plus an opaque `next_cursor`.
Cursors are stable under inserts (unlike offsets) which matters for feeds that
grow without bound, such as attempts and feedback.
"""

from __future__ import annotations

import base64
import json
from typing import Annotated, Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

from app.core.errors import InvalidInput

T = TypeVar("T")

DEFAULT_LIMIT = 25
MAX_LIMIT = 100


class Page(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None


class CursorParams:
    def __init__(
        self,
        cursor: Annotated[str | None, Query(description="Opaque cursor from a previous page")] = None,
        limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    ) -> None:
        self.cursor = decode_cursor(cursor) if cursor else None
        self.limit = limit


def encode_cursor(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), default=str).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> dict[str, Any]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, json.JSONDecodeError) as exc:
        raise InvalidInput("Invalid cursor") from exc
    if not isinstance(data, dict):
        raise InvalidInput("Invalid cursor")
    return data
