"""Bind the platform's library stations to the station template they were written to.

    poetry run python scripts/link_stations_to_templates.py --env staging            # dry run
    poetry run python scripts/link_stations_to_templates.py --env staging --apply

The imported b2c stations were authored to the same models the seeded platform
templates were built from (`seed_station_templates.py`), one per exam and four
for Ortho ST3, whose stations say which kind they are in `station_type`. This
sets each of their versions' `template_version_id` to that template's latest
published version, so the station reads as generated from it.

A bound station renders through its template's layout, and
`domain_content.content_for_template` reads the nested b2c sections by block
id. Every bound station is rendered here before anything commits: it must stay
renderable, no examiner block may reach a patient's prompt, and an examiner
(Ortho's viva) must hold every one of its questions. One failure rolls the
whole run back.

Ortho needs osce-assessment 0.9.0, the first engine that gives the examiner
persona its `examiner` blocks.

Idempotent: a version already bound to a template is left as it is.
`--upgrade` also moves a version bound to an older published version of the
same template onto its latest, once `seed_station_templates.py` has published
a changed structure.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import app.migration  # noqa: E402,F401  (refuses to run on staging, before --help can exit early)


class _Rollback(Exception):
    """Ends the transaction without committing. Never escapes `link`."""


async def link(*, apply: bool, upgrade: bool = False) -> int:
    """Bind, prove every bound station still renders, and commit only when applying and proven."""
    from app.core.db import get_session_factory, import_all_models
    from app.migration.link_templates import bind_unbound_versions

    import_all_models()
    report = None
    failed = False

    factory = get_session_factory()
    try:
        async with factory() as session, session.begin():
            report = await bind_unbound_versions(session, upgrade=upgrade)
            failed = bool(report.problems)
            if failed or not apply:
                raise _Rollback()
    except _Rollback:
        pass

    print("APPLIED" if apply and not failed else "rolled back")  # noqa: T201
    if report is not None:
        for label, count in sorted(report.counts.items()):
            print(f"  {label}: {count}")  # noqa: T201
        for problem in report.problems:
            print(f"  PROBLEM: {problem}")  # noqa: T201
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    """Point the app at the chosen database, then link."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--env", choices=("staging", "production"), help="Railway environment to link.")
    parser.add_argument("--apply", action="store_true", help="Commit. Without it the run is rolled back.")
    parser.add_argument(
        "--upgrade",
        action="store_true",
        help="Also move versions on an older template version to the latest.",
    )
    arguments = parser.parse_args(argv)
    if arguments.env:
        from copy_authoring_content import database_url

        # Before any `app` import: settings read DATABASE_URL once.
        os.environ["DATABASE_URL"] = database_url(arguments.env)
    return asyncio.run(link(apply=arguments.apply, upgrade=arguments.upgrade))


if __name__ == "__main__":
    sys.exit(main())
