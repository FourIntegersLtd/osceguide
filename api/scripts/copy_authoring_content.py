"""Make one environment's platform authoring content match another's.

    poetry run python scripts/copy_authoring_content.py                 # dry run, prod -> staging
    poetry run python scripts/copy_authoring_content.py --apply

Copies the platform-owned (org_id is null) exams, rubrics, rubric versions,
station templates and station template versions. Institution content is left
alone: its organisations exist in one environment only.

Why not delete and re-insert: attempts, stations, entitlements and sittings
point at exams and rubric versions with ON DELETE RESTRICT, and staging
already holds imported stations and media. So each prod row is matched to
the staging row it corresponds to and updated in place, keeping the staging
id; only rows with no counterpart are inserted, under their prod id.

Matching, in order:

- exam: by code.
- rubric: same id, else the rubric of the staging exam with the same code,
  else the same title.
- rubric version / template version: same (parent, version number).
- station template: same id, else the same (title, exam).

Staging platform rubrics and templates with no prod counterpart are deleted
("replace"), unless something still points at them, in which case they are
reported and left. Staging-only exams are only reported, never deleted.

The database URLs come from `railway variables`, so no URL is typed, logged
or written anywhere. The source is opened read-only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

# Each environment names its Postgres service differently.
POSTGRES_SERVICES = {"production": "platform-postgres-production", "staging": "platform-postgres"}
# Users differ between environments, so who published or archived a version
# cannot be carried over.
USER_COLUMNS = {"published_by", "archived_by", "created_by", "updated_by", "author_id", "suspended_by"}
NEVER_COPIED = {"id", "created_at"}

Row = dict[str, Any]


@dataclass
class Plan:
    """What a run did, per table, for the report."""

    updated: dict[str, int] = field(default_factory=dict)
    inserted: dict[str, int] = field(default_factory=dict)
    deleted: dict[str, list[str]] = field(default_factory=dict)
    kept: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    changes: list[str] = field(default_factory=list)

    def count(self, bucket: dict[str, int], table: str) -> None:
        """Add one to a table's tally in the given bucket."""
        bucket[table] = bucket.get(table, 0) + 1


def database_url(environment: str) -> str:
    """Read the public Postgres URL of a Railway environment without printing it."""
    service = POSTGRES_SERVICES[environment]
    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["railway", "variables", "--environment", environment, "--service", service, "--json"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    )
    variables = json.loads(completed.stdout)
    url = variables.get("DATABASE_PUBLIC_URL")
    proxy_domain, proxy_port = (
        variables.get("RAILWAY_TCP_PROXY_DOMAIN"),
        variables.get("RAILWAY_TCP_PROXY_PORT"),
    )
    if not url and proxy_domain and proxy_port and variables.get("DATABASE_URL"):
        # A proxy added by hand does not always get DATABASE_PUBLIC_URL; the
        # private URL with the proxy's host and port is the same database.
        private = urlsplit(str(variables["DATABASE_URL"]))
        credentials = private.netloc.rsplit("@", 1)[0]
        url = urlunsplit(private._replace(netloc=f"{credentials}@{proxy_domain}:{proxy_port}"))
    if not url:
        raise SystemExit(
            f"{environment}: {service} has no DATABASE_PUBLIC_URL. Enable its TCP proxy in Railway "
            "(Settings -> Networking) for the run, then remove it."
        )
    return str(url)


def fetch_owned_rows(connection: psycopg.Connection[Row], table: str, org_id: uuid.UUID | None) -> list[Row]:
    """Every row of a table one owner holds (None: the platform), oldest first so versions insert in order."""
    with connection.cursor() as cursor:
        if org_id is None:
            cursor.execute(f"SELECT * FROM {table} WHERE org_id IS NULL ORDER BY created_at, id")  # noqa: S608
        else:
            cursor.execute(
                f"SELECT * FROM {table} WHERE org_id = %s ORDER BY created_at, id",  # noqa: S608
                (org_id,),
            )
        return list(cursor.fetchall())


def column_types(connection: psycopg.Connection[Row], table: str) -> dict[str, str]:
    """Column name to data type, so JSON columns can be wrapped on write."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s",
            (table,),
        )
        return {row["column_name"]: row["data_type"] for row in cursor.fetchall()}


class Writer:
    """Writes rows into the target, limited to the columns both schemas share."""

    def __init__(self, source: psycopg.Connection[Row], target: psycopg.Connection[Row], plan: Plan) -> None:
        self.target = target
        self.plan = plan
        self.shared_columns: dict[str, dict[str, str]] = {}
        self.source = source
        # The owner rows are written under: None for the platform, else the
        # target environment's id for the institution being copied.
        self.target_org_id: uuid.UUID | None = None

    def columns(self, table: str) -> dict[str, str]:
        """Columns present in both databases; warns once about any schema drift."""
        if table not in self.shared_columns:
            source_columns = column_types(self.source, table)
            target_columns = column_types(self.target, table)
            only_in_source = sorted(set(source_columns) - set(target_columns))
            if only_in_source:
                self.plan.warnings.append(f"{table}: not in target schema, skipped: {only_in_source}")
            self.shared_columns[table] = {
                name: data_type for name, data_type in target_columns.items() if name in source_columns
            }
        return self.shared_columns[table]

    def prepared(self, table: str, row: Row) -> dict[str, Any]:
        """The row's copyable values, JSON wrapped and user references cleared."""
        values: dict[str, Any] = {}
        for name, data_type in self.columns(table).items():
            if name in NEVER_COPIED:
                continue
            value = row.get(name)
            if name in USER_COLUMNS:
                value = None
            elif name == "org_id":
                value = self.target_org_id
            elif data_type in {"json", "jsonb"} and value is not None:
                value = Jsonb(value)
            values[name] = value
        return values

    def update(self, table: str, target_id: uuid.UUID, row: Row) -> None:
        """Overwrite the target row with the source row's content."""
        values = self.prepared(table, row)
        with self.target.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {table} WHERE id = %s", (target_id,))  # noqa: S608
            current = cursor.fetchone() or {}
        differing = sorted(
            name
            for name, value in values.items()
            if name not in {"updated_at"}
            and (value.obj if isinstance(value, Jsonb) else value) != current.get(name)
        )
        if differing:
            self.plan.changes.append(f"{table} {target_id}: {', '.join(differing)}")
        assignments = ", ".join(f"{name} = %({name})s" for name in values)
        with self.target.cursor() as cursor:
            cursor.execute(
                f"UPDATE {table} SET {assignments} WHERE id = %(target_row_id)s",  # noqa: S608
                {**values, "target_row_id": target_id},
            )
        self.plan.count(self.plan.updated, table)

    def insert(self, table: str, row: Row) -> uuid.UUID:
        """Insert the source row under its own id and return that id."""
        values = {"id": row["id"], **self.prepared(table, row)}
        if "created_at" in self.columns(table):
            values["created_at"] = row["created_at"]
        names = ", ".join(values)
        placeholders = ", ".join(f"%({name})s" for name in values)
        with self.target.cursor() as cursor:
            cursor.execute(f"INSERT INTO {table} ({names}) VALUES ({placeholders})", values)  # noqa: S608
        self.plan.count(self.plan.inserted, table)
        return uuid.UUID(str(row["id"]))

    def delete_unless_referenced(self, table: str, row_id: uuid.UUID, label: str) -> None:
        """Delete a target-only row; if a foreign key refuses, keep it and say so."""
        try:
            with self.target.transaction(), self.target.cursor() as cursor:
                cursor.execute(f"DELETE FROM {table} WHERE id = %s", (row_id,))  # noqa: S608
        except psycopg.errors.ForeignKeyViolation:
            self.plan.kept.setdefault(table, []).append(label)
        else:
            self.plan.deleted.setdefault(table, []).append(label)


def by_id(rows: Iterable[Row]) -> dict[uuid.UUID, Row]:
    """Index rows by their primary key."""
    return {uuid.UUID(str(row["id"])): row for row in rows}


def copy_content(
    writer: Writer,
    plan: Plan,
    source_org_id: uuid.UUID | None = None,
    target_org_id: uuid.UUID | None = None,
) -> None:
    """Copy one owner's authoring rows from source into target, in dependency order."""
    source, target = writer.source, writer.target
    writer.target_org_id = target_org_id

    source_exams = fetch_owned_rows(source, "exams", source_org_id)
    source_rubrics = fetch_owned_rows(source, "rubrics", source_org_id)
    source_rubric_versions = fetch_owned_rows(source, "rubric_versions", source_org_id)
    source_templates = fetch_owned_rows(source, "station_templates", source_org_id)
    source_template_versions = fetch_owned_rows(source, "station_template_versions", source_org_id)

    target_exams = fetch_owned_rows(target, "exams", target_org_id)
    target_rubrics = by_id(fetch_owned_rows(target, "rubrics", target_org_id))
    target_rubric_versions = by_id(fetch_owned_rows(target, "rubric_versions", target_org_id))
    target_templates = by_id(fetch_owned_rows(target, "station_templates", target_org_id))
    target_template_versions = by_id(fetch_owned_rows(target, "station_template_versions", target_org_id))

    target_exam_by_code = {str(exam["code"]).lower(): exam for exam in target_exams}
    source_rubric_version_by_id = by_id(source_rubric_versions)

    # --- rubrics -----------------------------------------------------------
    # A rubric's current_version_id points at a version not yet copied, so it
    # is written empty here and filled in once the versions exist.
    rubric_id_map: dict[uuid.UUID, uuid.UUID] = {}
    rubric_for_exam_code: dict[uuid.UUID, uuid.UUID] = {}
    for exam in source_exams:
        source_version = source_rubric_version_by_id.get(exam["rubric_version_id"])
        target_exam = target_exam_by_code.get(str(exam["code"]).lower())
        if source_version is None or target_exam is None or target_exam["rubric_version_id"] is None:
            continue
        target_version = target_rubric_versions.get(target_exam["rubric_version_id"])
        if target_version is not None:
            rubric_for_exam_code[source_version["rubric_id"]] = target_version["rubric_id"]

    claimed_rubrics: set[uuid.UUID] = set()
    target_rubric_by_title = {str(rubric["title"]): rubric_id for rubric_id, rubric in target_rubrics.items()}
    for rubric in source_rubrics:
        source_id = uuid.UUID(str(rubric["id"]))
        target_id = (
            source_id
            if source_id in target_rubrics
            else rubric_for_exam_code.get(source_id) or target_rubric_by_title.get(str(rubric["title"]))
        )
        if target_id is not None and target_id not in claimed_rubrics:
            writer.update("rubrics", target_id, {**rubric, "current_version_id": None})
        else:
            target_id = writer.insert("rubrics", {**rubric, "current_version_id": None})
        claimed_rubrics.add(target_id)
        rubric_id_map[source_id] = target_id

    # --- rubric versions ---------------------------------------------------
    rubric_version_id_map: dict[uuid.UUID, uuid.UUID] = {}
    target_rubric_version_by_key = {
        (version["rubric_id"], version["version"]): version_id
        for version_id, version in target_rubric_versions.items()
    }
    for version in source_rubric_versions:
        mapped_rubric = rubric_id_map[version["rubric_id"]]
        mapped_version = {**version, "rubric_id": mapped_rubric}
        existing = target_rubric_version_by_key.get((mapped_rubric, version["version"]))
        if existing is not None:
            writer.update("rubric_versions", existing, mapped_version)
            rubric_version_id_map[uuid.UUID(str(version["id"]))] = existing
        else:
            rubric_version_id_map[uuid.UUID(str(version["id"]))] = writer.insert(
                "rubric_versions", mapped_version
            )

    with target.cursor() as cursor:
        for rubric in source_rubrics:
            if rubric["current_version_id"] is not None:
                cursor.execute(
                    "UPDATE rubrics SET current_version_id = %s WHERE id = %s",
                    (rubric_version_id_map[rubric["current_version_id"]], rubric_id_map[rubric["id"]]),
                )

    # --- exams -------------------------------------------------------------
    exam_id_map: dict[uuid.UUID, uuid.UUID] = {}
    for exam in source_exams:
        mapped_exam = {
            **exam,
            "rubric_version_id": rubric_version_id_map.get(exam["rubric_version_id"])
            if exam["rubric_version_id"]
            else None,
        }
        target_exam = target_exam_by_code.get(str(exam["code"]).lower())
        if target_exam is not None:
            target_id = uuid.UUID(str(target_exam["id"]))
            writer.update("exams", target_id, mapped_exam)
        else:
            target_id = writer.insert("exams", mapped_exam)
        exam_id_map[uuid.UUID(str(exam["id"]))] = target_id

    source_exam_codes = {str(exam["code"]).lower() for exam in source_exams}
    for code in target_exam_by_code:
        if code not in source_exam_codes:
            plan.kept.setdefault("exams", []).append(f"{code} (staging only, never deleted)")

    # --- station templates -------------------------------------------------
    template_id_map: dict[uuid.UUID, uuid.UUID] = {}
    claimed_templates: set[uuid.UUID] = set()
    target_template_by_key = {
        (str(template["title"]), template["exam_id"]): template_id
        for template_id, template in target_templates.items()
    }
    for template in source_templates:
        source_id = uuid.UUID(str(template["id"]))
        mapped_exam_id = exam_id_map.get(template["exam_id"]) if template["exam_id"] else None
        mapped_template = {**template, "exam_id": mapped_exam_id}
        target_id = (
            source_id
            if source_id in target_templates
            else target_template_by_key.get((str(template["title"]), mapped_exam_id))
        )
        if target_id is not None and target_id not in claimed_templates:
            writer.update("station_templates", target_id, mapped_template)
        else:
            target_id = writer.insert("station_templates", mapped_template)
        claimed_templates.add(target_id)
        template_id_map[source_id] = target_id

    # --- station template versions -----------------------------------------
    claimed_template_versions: set[uuid.UUID] = set()
    target_template_version_by_key = {
        (version["template_id"], version["version"]): version_id
        for version_id, version in target_template_versions.items()
    }
    for version in source_template_versions:
        mapped_template_id = template_id_map[version["template_id"]]
        mapped_version = {**version, "template_id": mapped_template_id}
        existing = target_template_version_by_key.get((mapped_template_id, version["version"]))
        if existing is not None:
            writer.update("station_template_versions", existing, mapped_version)
            claimed_template_versions.add(existing)
        else:
            claimed_template_versions.add(writer.insert("station_template_versions", mapped_version))

    # --- staging-only rows: replace means remove -----------------------------
    # Templates first: deleting one cascades to its versions.
    for template_id, template in target_templates.items():
        if template_id not in claimed_templates:
            writer.delete_unless_referenced("station_templates", template_id, str(template["title"]))
    for version_id, version in target_template_versions.items():
        if version_id not in claimed_template_versions and version["template_id"] in claimed_templates:
            writer.delete_unless_referenced(
                "station_template_versions", version_id, f"{version['template_id']} v{version['version']}"
            )
    claimed_rubric_versions = set(rubric_version_id_map.values())
    for version_id, version in target_rubric_versions.items():
        if version_id not in claimed_rubric_versions and version["rubric_id"] in claimed_rubrics:
            writer.delete_unless_referenced(
                "rubric_versions", version_id, f"{version['rubric_id']} v{version['version']}"
            )
    for rubric_id, rubric in target_rubrics.items():
        if rubric_id not in claimed_rubrics:
            writer.delete_unless_referenced("rubrics", rubric_id, str(rubric["title"]))


def copy_organizations(writer: Writer) -> dict[uuid.UUID, uuid.UUID]:
    """Map every source institution that owns authoring content to its target twin.

    Matched by slug; a missing one is created as the organisation row alone --
    no members, no sittings, no results, since real data never goes to staging.
    """
    with writer.source.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM organizations WHERE id IN ("
            " SELECT org_id FROM exams UNION SELECT org_id FROM rubrics"
            " UNION SELECT org_id FROM station_templates) ORDER BY created_at"
        )
        source_organizations = list(cursor.fetchall())
    organization_id_map: dict[uuid.UUID, uuid.UUID] = {}
    for organization in source_organizations:
        with writer.target.cursor() as cursor:
            cursor.execute("SELECT id FROM organizations WHERE slug = %s", (organization["slug"],))
            existing = cursor.fetchone()
        if existing is not None:
            organization_id_map[organization["id"]] = existing["id"]
        else:
            organization_id_map[organization["id"]] = writer.insert(
                "organizations", {**organization, "parent_org_id": None}
            )
    return organization_id_map


def org_owned_counts(connection: psycopg.Connection[Row]) -> dict[str, int]:
    """Institution-owned rows per table, reported so nothing is skipped silently."""
    counts = {}
    with connection.cursor() as cursor:
        for table in ("exams", "rubrics", "station_templates"):
            cursor.execute(f"SELECT count(*) AS total FROM {table} WHERE org_id IS NOT NULL")  # noqa: S608
            counts[table] = int(cursor.fetchone()["total"])  # type: ignore[index]
    return counts


def report(
    plan: Plan, *, applied: bool, source_env: str, target_env: str, org_counts: dict[str, int]
) -> None:
    """Print what changed (or would change) in the target."""
    print(f"{source_env} -> {target_env}: {'APPLIED' if applied else 'dry run, rolled back'}")  # noqa: T201
    for title, tallies in (("updated", plan.updated), ("inserted", plan.inserted)):
        for table, total in tallies.items():
            print(f"  {title:8} {table}: {total}")  # noqa: T201
    for title, named_rows in (("deleted", plan.deleted), ("kept", plan.kept)):
        for table, labels in named_rows.items():
            print(f"  {title:8} {table}: {len(labels)}")  # noqa: T201
            for label in labels:
                print(f"             - {label}")  # noqa: T201
    print(f"  institution-owned rows in {source_env}: {org_counts}")  # noqa: T201
    for change in plan.changes:
        print(f"  differs  {change}")  # noqa: T201
    for warning in plan.warnings:
        print(f"  warning: {warning}")  # noqa: T201


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, copy inside one target transaction, commit only with --apply."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--source", default="production", help="Railway environment to copy from.")
    parser.add_argument("--target", default="staging", help="Railway environment to copy into.")
    parser.add_argument("--apply", action="store_true", help="Commit. Without it the run is rolled back.")
    arguments = parser.parse_args(argv)
    if arguments.target == "production":
        raise SystemExit("Refusing to write into production.")

    plan = Plan()
    with (
        psycopg.connect(database_url(arguments.source), row_factory=dict_row) as source,
        psycopg.connect(database_url(arguments.target), row_factory=dict_row) as target,
    ):
        source.read_only = True
        org_counts = org_owned_counts(source)
        with target.transaction() as outer:
            writer = Writer(source, target, plan)
            copy_content(writer, plan)
            for source_org_id, target_org_id in copy_organizations(writer).items():
                copy_content(writer, plan, source_org_id, target_org_id)
            if not arguments.apply:
                # The same writes, undone — so every constraint a real run
                # would hit has been hit by the time the report prints.
                raise psycopg.Rollback(outer)
    report(
        plan,
        applied=arguments.apply,
        source_env=arguments.source,
        target_env=arguments.target,
        org_counts=org_counts,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
