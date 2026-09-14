"""OSCE Guide assessment engine.

One engine, many consumers. This package describes what an assessment is
(``contracts``), how an attempt is driven from scenario to scored result
(``runtime``), and the test doubles that let all of that run without a voice
server or a language model (``testing``).

``catalog`` holds the competency frameworks the platform publishes. It is
content rather than machinery: the runtime carries a framework id and never
looks one up. ``compat`` holds migration shims for vocabulary the platform has
not finished retiring, and the engine proper never imports from it.

The package never learns who is consuming it. Consumer identifiers travel
opaquely in ``AssessmentAttempt.attempt_context`` and come back untouched.
"""

__version__ = "0.6.0"

__all__ = ["__version__"]
