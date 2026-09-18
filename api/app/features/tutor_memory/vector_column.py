"""A `vector` column, without taking a dependency for it.

pgvector ships a Python package whose only job here would be this type and a
handful of operator helpers. The extension is what does the work; the package
is a convenience, and `docs/OPEN-QUESTIONS.md` F-1 is the standing rule that a
new dependency is asked for rather than assumed. So the type is thirty lines
and the distance operator is written out in the one query that uses it.

Binding is textual on purpose: pgvector accepts `'[1,2,3]'::vector`, which is
also what makes a query readable in a log and reproducible by hand in psql.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import String
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import TypeDecorator, UserDefinedType

# `text-embedding-3-small`. Fixed in the schema rather than configured: the
# column's width is DDL, so a setting that disagreed with the migration would
# be a setting that cannot be set.
EMBEDDING_DIMENSIONS = 1536


class VECTOR(UserDefinedType[Any]):
    """The extension's own type, named so Alembic renders it in a migration."""

    cache_ok = True

    def __init__(self, dimensions: int = EMBEDDING_DIMENSIONS) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **_: Any) -> str:
        return f"vector({self.dimensions})"


@compiles(VECTOR)
def _compile_vector(type_: VECTOR, compiler: Any, **kw: Any) -> str:
    return type_.get_col_spec()


class Vector(TypeDecorator[Sequence[float]]):
    """A list of floats on the Python side, a `vector` literal on the wire."""

    impl = VECTOR
    cache_ok = True

    def __init__(self, dimensions: int = EMBEDDING_DIMENSIONS) -> None:
        self.dimensions = dimensions
        super().__init__(dimensions)

    def load_dialect_impl(self, dialect: Any) -> Any:
        # Outside Postgres there is no extension to lean on. The tutor's index
        # is Postgres-only by design, and this keeps `create_all` usable in a
        # non-Postgres context rather than failing on an unknown type.
        if dialect.name != "postgresql":
            return dialect.type_descriptor(String())
        return dialect.type_descriptor(VECTOR(self.dimensions))

    def process_bind_param(self, value: Sequence[float] | None, dialect: Any) -> str | None:
        return None if value is None else to_literal(value)

    def process_result_value(self, value: Any, dialect: Any) -> list[float] | None:
        if value is None:
            return None
        return [float(part) for part in str(value).strip("[]").split(",") if part]


def to_literal(vector: Sequence[float]) -> str:
    """`[1.0,2.0]` — the text form pgvector casts."""
    return "[" + ",".join(repr(float(component)) for component in vector) + "]"
