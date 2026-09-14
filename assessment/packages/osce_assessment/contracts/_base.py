"""Shared model configuration for the contract types."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Frozen(BaseModel):
    """Immutable, strict-by-default contract model.

    Contracts are values: once constructed they are never edited in place, and
    an unexpected field is an error rather than silent data loss.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
