"""The model clients the engine marks with.

Separated from the adapter so which model marks an attempt is a configuration
question in one place, not a detail buried in translation code. b2c marks with
`gpt-5-mini` at low effort and b2b with `gpt-4o`, which is why their results are
not comparable — decision E-2.
"""

from __future__ import annotations

from typing import Any

from app.core.settings import get_settings


def primary_client() -> Any | None:
    """The OpenAI client the engine marks with first, or `None` if it is not configured."""
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    try:
        from openai import OpenAI  # optional dependency
    except ImportError:
        return None
    return OpenAI(api_key=settings.openai_api_key)


def fallback_client() -> Any | None:
    """Anthropic, used when the primary refuses or times out."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    try:
        from anthropic import Anthropic  # optional dependency
    except ImportError:
        return None
    return Anthropic(api_key=settings.anthropic_api_key)
