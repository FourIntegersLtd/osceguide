"""The attempt runtime: scenario → profile → interaction → transcript → result."""

from .attempt_runtime import AttemptRuntime, RuntimeOutcome
from .collector import TranscriptCollector
from .delivery import DeliveryError, RetryPolicy, TranscriptDelivery
from .fake_adapter import FakeInteractionAdapter, InteractionFailure

__all__ = [
    "AttemptRuntime",
    "DeliveryError",
    "FakeInteractionAdapter",
    "InteractionFailure",
    "RetryPolicy",
    "RuntimeOutcome",
    "TranscriptCollector",
    "TranscriptDelivery",
]
