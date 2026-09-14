"""Migration shims for vocabulary the platform has not finished retiring.

Everything here is temporary by definition and has a stated end condition in
its own module docstring. The engine proper must not import from this package;
consumers call it while translating their existing request shapes.
"""

from .legacy_app_types import (
    LEGACY_APP_TYPE_TO_FRAMEWORK_ID,
    UnknownAppTypeError,
    framework_id_for_app_type,
    legacy_app_types,
)

__all__ = [
    "LEGACY_APP_TYPE_TO_FRAMEWORK_ID",
    "UnknownAppTypeError",
    "framework_id_for_app_type",
    "legacy_app_types",
]
