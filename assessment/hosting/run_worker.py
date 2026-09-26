"""The container's one process: the LiveKit worker chosen by ``OSCE_LIVEKIT_WORKER``.

The same entry serves K8s and LiveKit Cloud. It runs the worker in this process,
with no wrapper in between, so the stop signal the platform sends lands on the
worker itself. The SDK answers that signal by draining: it tells LiveKit it
takes no new sessions, lets the running ones finish, then exits.

A wrapper here once swallowed that signal (make, then gunicorn, then a
subprocess): the worker never heard it, kept taking new sessions for the whole
15-minute grace period, and was killed mid-consultation at the end of it.

Run as ``python -m hosting.run_worker start``.
"""

from __future__ import annotations

import importlib

from hosting.workers import selected_worker


def cli_main() -> None:
    """Import the selected worker's entrypoint and hand this process to its CLI."""
    worker_spec = selected_worker()
    worker_entrypoint = importlib.import_module(worker_spec.module)
    # Each worker entrypoint owns dotenv, Sentry and its own option validation,
    # and reads the ``start`` command from this process's arguments.
    worker_entrypoint.cli_main()


if __name__ == "__main__":
    cli_main()
