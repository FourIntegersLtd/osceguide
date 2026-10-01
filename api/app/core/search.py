"""The one way a list endpoint matches text a person typed into a search box."""

from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement
from sqlalchemy.sql.operators import ColumnOperators


def contains_text(column: ColumnOperators, typed_text: str) -> ColumnElement[Any]:
    """A filter that is true where `column` contains `typed_text`, ignoring case.

    `%` and `_` are escaped, so they match themselves. Left as they are, they
    are wildcards to the database, and a search for `_` would match every row.
    """
    return column.icontains(typed_text.strip(), autoescape=True)  # type: ignore[return-value]
