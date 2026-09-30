"""OSCE Guide assessment engine.

One engine, many consumers. This package describes what an assessment is
(``contracts``), how an attempt is driven from scenario to scored result
(``runtime``), and the test doubles that let all of that run without a voice
server or a language model (``testing``).

No competency framework is shipped here. A framework is authored — by the
platform or by an institution — stored as a row, and handed in through a
``FrameworkProvider``; the runtime carries a framework id and never looks one
up. This package holds the machinery, never the content.

The package never learns who is consuming it. Consumer identifiers travel
opaquely in ``AssessmentAttempt.attempt_context`` and come back untouched.
"""

__version__ = "0.9.0"

__all__ = ["__version__"]
