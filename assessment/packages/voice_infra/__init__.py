"""Shared LiveKit worker infrastructure, driven by configuration.

A config-driven port of the legacy ``livekit_voice`` package. Where the legacy
code branched on a ``product`` string to choose backend URLs, secrets and
payload shapes, this package takes a ``BackendEndpoints`` value. Workers look
one up by an opaque label carried in job metadata, so no worker code ever
knows which product it is serving.
"""

from .config import BackendEndpoints, BackendRegistry, BackendRegistryError

__all__ = ["BackendEndpoints", "BackendRegistry", "BackendRegistryError"]
