"""The errors the read models can answer with.

There is one, and it is `sittings`': a console for a circuit that is not this
organisation's is the same refusal, with the same code, as asking for that
circuit directly. Re-exported rather than redefined so the frontend keeps one
`circuit_not_found` to switch on, and so the router stays inside the rule that
it imports only its own slice.
"""

from __future__ import annotations

from app.features.sittings.errors import CircuitNotFound

__all__ = ["CircuitNotFound"]
