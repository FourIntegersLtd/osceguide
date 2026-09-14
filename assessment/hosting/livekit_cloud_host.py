"""LiveKit Cloud single-process entry: one worker per deployment."""

from __future__ import annotations

import importlib

from livekit.agents import cli

from hosting.workers import selected_worker


def cli_main() -> None:
    spec = selected_worker()
    module = importlib.import_module(spec.module)
    # Each worker entrypoint owns dotenv, Sentry and its own option validation.
    module.cli_main() if hasattr(module, "cli_main") else cli.run_app(module.build_worker_options())


if __name__ == "__main__":
    cli_main()
