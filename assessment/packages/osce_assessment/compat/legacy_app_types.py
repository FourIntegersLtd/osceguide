"""Translates the legacy ``app_type`` request field to a framework id.

Both backends currently identify an exam with a short product string, spelled
about forty different places across backend, worker and frontend code. This
table is the one shared copy of that translation, so the two consumers cannot
drift apart while they still speak it.

It is a shim, not architecture. It returns an id rather than a framework object
so that it stays pure data with no dependency on the catalogue.

End condition: delete this module once both consumers resolve a framework id at
their own request boundary and pass it in. Nothing in ``osce_assessment``
outside this package may import it, and the leakage guard enforces that.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping


class UnknownAppTypeError(LookupError):
    """Raised for an ``app_type`` with no framework mapping."""


LEGACY_APP_TYPE_TO_FRAMEWORK_ID: Mapping[str, str] = MappingProxyType(
    {
        "sca": "sca-rcgp-v1",
        "plab": "plab2-gmc-v1",
        "casc": "casc-rcpsych-v1",
        "ortho": "ortho-frcs-v1",
    }
)


def framework_id_for_app_type(app_type: str | None) -> str:
    """Return the framework id for a legacy product exam string."""
    key = (app_type or "").strip().lower()
    try:
        return LEGACY_APP_TYPE_TO_FRAMEWORK_ID[key]
    except KeyError:
        raise UnknownAppTypeError(
            f"no framework mapped for app_type {app_type!r}; "
            f"known: {sorted(LEGACY_APP_TYPE_TO_FRAMEWORK_ID)}"
        ) from None


def legacy_app_types() -> tuple[str, ...]:
    return tuple(LEGACY_APP_TYPE_TO_FRAMEWORK_ID)
