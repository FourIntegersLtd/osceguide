"""Cursor pagination.

Every list endpoint returns `Page[T]`: the items plus an opaque `next_cursor`.
Cursors are stable under inserts (unlike offsets) which matters for feeds that
grow without bound, such as attempts and feedback.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime
from typing import Annotated, Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, literal, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.core.errors import InvalidInput

T = TypeVar("T")

DEFAULT_LIMIT = 25
MAX_LIMIT = 100


# A page of items plus the opaque cursor for the next one, or none if this was the last.
class Page(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None


class CursorParams:
    """The `cursor`/`limit` query parameters, decoded, for a route to depend on."""

    def __init__(
        self,
        cursor: Annotated[str | None, Query(description="Opaque cursor from a previous page")] = None,
        limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    ) -> None:
        self.cursor = decode_cursor(cursor) if cursor else None
        self.limit = limit


def encode_cursor(cursor_fields: dict[str, Any]) -> str:
    """Pack cursor fields into the opaque string a client sends back unchanged."""
    raw = json.dumps(cursor_fields, separators=(",", ":"), default=str).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> dict[str, Any]:
    """Unpack a cursor, or refuse it as `InvalidInput` if it has been tampered with."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, json.JSONDecodeError) as exc:
        raise InvalidInput("Invalid cursor") from exc
    if not isinstance(decoded, dict):
        raise InvalidInput("Invalid cursor")
    return decoded


async def keyset_page(
    session: AsyncSession,
    stmt: Select[Any],
    *,
    sort_col: InstrumentedAttribute[Any],
    id_col: InstrumentedAttribute[Any],
    limit: int,
    cursor: dict[str, Any] | None,
    descending: bool = True,
) -> tuple[list[Any], str | None]:
    """Keyset paging on `(sort_col, id_col)`, returning scalars and the next cursor.

    The id breaks ties. Rows written in one transaction share a `now()`, so a
    cursor on the timestamp alone skips or repeats every row that shares the
    boundary row's timestamp — a batch import, a seeded roster, a bulk
    station-set create. Most hand-written copies of this got the tie-break
    wrong; this is the one lifted into core.

    `tuple_()`, not a Python tuple: `(col_a, col_b) > (x, y)` compares the
    Column objects in Python and silently produces the wrong filter.
    """
    if cursor:
        mark = datetime.fromisoformat(cursor["t"])
        mark_id = uuid.UUID(cursor["i"])
        keyset = tuple_(sort_col, id_col)
        boundary = tuple_(literal(mark), literal(mark_id))
        stmt = stmt.where(keyset < boundary if descending else keyset > boundary)
    order = (sort_col.desc(), id_col.desc()) if descending else (sort_col.asc(), id_col.asc())
    rows = list((await session.execute(stmt.order_by(*order).limit(limit + 1))).scalars())
    if len(rows) <= limit:
        return rows, None
    page = rows[:limit]
    last = page[-1]
    return page, encode_cursor({"t": getattr(last, sort_col.key), "i": str(getattr(last, id_col.key))})
