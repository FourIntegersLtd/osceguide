"""Await a value whether the port implementation was sync or async."""

from __future__ import annotations

import inspect
from typing import Any, TypeVar

T = TypeVar("T")


async def maybe_await(value: Any) -> Any:
    """Return the value, awaiting it first when it is awaitable."""
    if inspect.isawaitable(value):
        return await value
    return value
