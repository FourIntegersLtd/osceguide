"""Which provider answers first: the two slots of an evaluation policy, in the order it asks them."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, NamedTuple

from ..contracts import EvaluationPolicy

ClientFactory = Callable[[], Any | None]


class Slot(NamedTuple):
    """One provider of the policy. ``label`` is ``"primary"`` for the one asked first, else ``"fallback"``."""

    provider: str
    label: str
    model: str | None
    factory: ClientFactory | None

    @property
    def configured(self) -> bool:
        """Whether the policy names a model for this provider and the caller supplied its client."""
        return bool(self.model) and self.factory is not None


def ordered_slots(policy: EvaluationPolicy, *, openai: ClientFactory, anthropic: ClientFactory | None) -> tuple[Slot, Slot]:
    """The OpenAI and Anthropic slots, the policy's ``first_provider`` first."""
    slots = {
        "openai": ("openai", policy.openai_model, openai),
        "anthropic": ("anthropic", policy.anthropic_model, anthropic),
    }
    order = ("anthropic", "openai") if policy.first_provider == "anthropic" else ("openai", "anthropic")
    first, second = (slots[name] for name in order)
    return Slot(first[0], "primary", first[1], first[2]), Slot(second[0], "fallback", second[1], second[2])
