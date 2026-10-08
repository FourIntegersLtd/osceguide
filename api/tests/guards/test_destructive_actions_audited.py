"""A destructive action leaves an audit row and refuses when something still depends on the thing.

"Destructive" is every `DELETE` route plus every service named `archive*`, `retire*` or `delete*`. For
each, the service function (following same-slice calls three deep) must

- write an audit row: `record_for_owner` (an organisation's own log, or the platform's), or one of
  its siblings `record_system` / `_record_for_org`; and
- run an in-use check: call something named for it (`*_in_use`, `*_references`, `*_usage`, ...) or
  raise a Conflict that says what still depends on it (`...InUse`, `...HasAttempts`).

Each check fails with its list of offenders. Existing offenders are in the two allow-lists with a
reason; the ceilings only shrink. Some are by design: a person deleting their own data is not an
organisation's audit trail, and a revoke has no dependants.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from tests.guards._scan import APP_ROOT, assert_allow_list, parse, python_files, rel, route_method

AUDIT_CALLS = {"record_for_owner", "record_system", "_record_for_org"}
IN_USE = re.compile(r"in_?use|inuse|hasattempts|has_attempts|is_used|referenc|usage|used_by|dependents", re.I)
DESTRUCTIVE_NAME = re.compile(r"^(archive|retire|delete)")
DEPTH = 3

# `file::function` -> why no audit row is right. The ceiling only shrinks.
NO_AUDIT: dict[str, str] = {
    "app/features/attempts/service_platform.py::delete_progress": (
        "primitive: station_sets.service_platform.delete_progress calls it and writes the audit row"
    ),
    "app/features/community/service.py::remove": (
        "GAP: a moderator removing someone's post leaves no audit row; own-post removal is by design"
    ),
    "app/features/cv/service.py::delete": "a person deleting their own CV; not an organisation's audit trail",
    "app/features/growth/service_dashboard.py::revoke_reporter": (
        "GAP: partner dashboard grant revoked without an audit row"
    ),
    "app/features/identity/service_mfa.py::disable_for_user": (
        "GAP: a person turning off their own authenticator is a security event with no audit row"
    ),
    "app/features/marketplace/service.py::withdraw_slot": (
        "the offerer takes back their own offer; not a staff or org action"
    ),
    "app/features/media/service.py::delete_draft": (
        "GAP: a platform draft deleted without an audit row; never published"
    ),
    "app/features/media_production/service.py::delete_image": (
        "storage helper for identity's own avatar; the caller owns the record"
    ),
    "app/features/peer_practice/service_privacy.py::delete_recording": (
        "a participant exercising their own privacy right on their own recording"
    ),
    "app/features/reviews/service.py::withdraw_gp_lead_review": (
        "GAP: withdrawing a draft review leaves no audit row; drafts carry no decision"
    ),
    "app/features/reviews/service.py::withdraw_slot_review": (
        "GAP: withdrawing a draft review leaves no audit row; drafts carry no decision"
    ),
    "app/features/roster/service_groups.py::delete_cohort": (
        "GAP: an organisation intake deleted without an audit row"
    ),
    "app/features/roster/service_groups.py::delete_group": (
        "GAP: an organisation group deleted without an audit row"
    ),
    "app/features/roster/service_scim.py::delete_group": (
        "GAP: the identity provider removes a group through SCIM with no audit row"
    ),
    "app/features/rubrics/service.py::archive_version": (
        "GAP: archiving a published rubric version leaves no audit row"
    ),
    "app/features/sittings/service_structure.py::delete_circuit": (
        "GAP: an unstarted circuit is deleted without an audit row"
    ),
    "app/features/station_sets/service.py::delete_set": "a person deleting their own practice set",
    "app/features/stations/service_templates.py::archive_version": (
        "GAP: archiving a station template version leaves no audit row"
    ),
    "app/features/stations/service_templates.py::delete_version": (
        "GAP: deleting a draft template version leaves no audit row; drafts only"
    ),
    "app/features/tutor_memory/service.py::forget_everything": "a person clearing their own tutor memory",
    "app/features/tutor_memory/service.py::forget_note": "a person clearing their own tutor note",
    "app/features/voice/service.py::close_own_room": "a candidate ending their own consultation",
    "app/features/voice/service.py::leave_queue": "a candidate leaving the line",
    "app/features/peer_practice/service.py::leave_queue": "a person leaving the waiting room",
}
NO_AUDIT_CEILING = 24

# `file::function` -> why nothing can depend on it, or why the dependants are checked elsewhere.
NO_IN_USE_CHECK: dict[str, str] = {
    "app/features/attempts/service_platform.py::delete_progress": (
        "refuses while an attempt runs; nothing else references an attempt"
    ),
    "app/features/catalog/service_authoring.py::retire_exam": (
        "retiring touches nothing already attempted; attempts keep their frozen definition"
    ),
    "app/features/community/service.py::remove": "a soft-remove; replies are hidden with the post",
    "app/features/cv/service.py::delete": "nothing references a CV",
    "app/features/growth/service_dashboard.py::revoke_reporter": "a grant; no dependants",
    "app/features/identity/service_mfa.py::disable_for_user": (
        "policy requirement is checked before the code is read"
    ),
    "app/features/marketplace/service.py::withdraw_slot": (
        "a claimed slot is cancelled with notice, not refused"
    ),
    "app/features/media/service.py::delete_draft": "refuses once published; a draft has no dependants",
    "app/features/media_production/service.py::delete_image": (
        "images are looked up by key; the caller owns the references"
    ),
    "app/features/peer_practice/service_privacy.py::delete_recording": (
        "a recording has no dependants beyond its own row"
    ),
    "app/features/reviews/service.py::withdraw_gp_lead_review": (
        "a draft review; nothing depends on it until sign-off"
    ),
    "app/features/reviews/service.py::withdraw_slot_review": (
        "a draft review; nothing depends on it until sign-off"
    ),
    "app/features/roster/service_groups.py::delete_group": "refuses a group with members via GroupNotEmpty",
    "app/features/roster/service_scim.py::deactivate_user": (
        "revokes access and keeps the record, so nothing dangles"
    ),
    "app/features/roster/service_scim.py::delete_group": "SCIM empties the group first by design",
    "app/features/roster/service_scim.py::revoke_token": "a credential; no dependants",
    "app/features/sittings/service_structure.py::delete_circuit": (
        "refuses once started (CircuitLockedError); an unstarted one has no attempts"
    ),
    "app/features/station_sets/service_platform.py::delete_progress": (
        "the primitive attempts.delete_progress refuses while one runs"
    ),
    "app/features/stations/service_templates.py::archive_version": (
        "GAP: archiving does not count the stations built on the version"
    ),
    "app/features/stations/service_templates.py::delete_version": (
        "drafts only: a draft cannot have stations bound to it"
    ),
    "app/features/stations/service_versions.py::delete_version": (
        "drafts only: a published revision is refused by lifecycle"
    ),
    "app/features/tutor_memory/service.py::forget_everything": "a person clearing their own memory",
    "app/features/tutor_memory/service.py::forget_note": "a person clearing their own note",
    "app/features/voice/service.py::close_own_room": "closing a room ends it; nothing depends on it",
    "app/features/voice/service.py::leave_queue": "a queue place; nothing depends on it",
    "app/features/peer_practice/service.py::leave_queue": "a queue place; nothing depends on it",
}
NO_IN_USE_CEILING = 26


def _service_functions() -> dict[Path, dict[str, ast.AsyncFunctionDef | ast.FunctionDef]]:
    found: dict[Path, dict[str, ast.AsyncFunctionDef | ast.FunctionDef]] = {}
    for path in python_files(APP_ROOT):
        if path.name.startswith("service"):
            found[path] = {
                n.name: n for n in parse(path).body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
            }
    return found


def _called(function: ast.AST) -> list[tuple[str | None, str]]:
    """`(module-ish qualifier, name)` of every call, plus raised exception names (qualifier None)."""
    out: list[tuple[str | None, str]] = []
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Name):
                out.append((None, target.id))
            elif isinstance(target, ast.Attribute):
                qualifier = target.value.id if isinstance(target.value, ast.Name) else None
                out.append((qualifier, target.attr))
                if target.attr == "record" and qualifier and "audit" in qualifier:
                    out.append((qualifier, "record_for_owner"))
        if isinstance(node, ast.Raise) and node.exc is not None:
            raised = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            if isinstance(raised, ast.Attribute):
                out.append((None, raised.attr))
            elif isinstance(raised, ast.Name):
                out.append((None, raised.id))
    return out


def _names_reached(path: Path, function: ast.AST, services: dict, depth: int = DEPTH) -> set[str]:
    """Every name the function calls or raises, following calls into the same slice's services."""
    reached: set[str] = set()
    frontier = [(path, function)]
    seen: set[int] = set()
    for _ in range(depth + 1):
        following = []
        for here, node in frontier:
            for qualifier, name in _called(node):
                reached.add(name)
                candidates = [
                    (p, fns[name])
                    for p, fns in services.items()
                    if p.parent == here.parent
                    and name in fns
                    and (qualifier is None or p.stem == qualifier or qualifier == "service")
                ]
                for p, fn in candidates:
                    if id(fn) not in seen:
                        seen.add(id(fn))
                        following.append((p, fn))
        frontier = following
    return reached


def _delete_route_targets() -> list[tuple[Path, ast.FunctionDef | ast.AsyncFunctionDef]]:
    """Every `@router.delete` handler, with the router file it lives in."""
    found: list[tuple[Path, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for router in python_files(APP_ROOT):
        if not router.name.startswith("router"):
            continue
        for handler in ast.walk(parse(router)):
            if (
                isinstance(handler, ast.FunctionDef | ast.AsyncFunctionDef)
                and route_method(handler) == "delete"
            ):
                found.append((router, handler))
    return found


def destructive_functions() -> dict[str, tuple[Path, ast.AST]]:
    """`file::function` for every destructive service: named so, or the target of a DELETE route."""
    services = _service_functions()
    chosen: dict[str, tuple[Path, ast.AST]] = {}
    for path, fns in services.items():
        for name, fn in fns.items():
            if DESTRUCTIVE_NAME.match(name):
                chosen[f"{rel(path)}::{name}"] = (path, fn)
    for router, handler in _delete_route_targets():
        for qualifier, name in _called(handler):
            if re.match(r"(ensure|set|get|list|read)_", name):
                continue  # a guard or a toggle the handler calls, not the removal itself
            for path, fns in services.items():
                if path.parent == router.parent and name in fns and qualifier in {path.stem, "service"}:
                    chosen[f"{rel(path)}::{name}"] = (path, fns[name])
    return chosen


def _missing(check) -> list[str]:  # type: ignore[no-untyped-def]
    services = _service_functions()
    return sorted(
        key
        for key, (path, fn) in destructive_functions().items()
        if not check(_names_reached(path, fn, services))
    )


def has_audit(names: set[str]) -> bool:
    return bool(names & AUDIT_CALLS)


def has_in_use_check(names: set[str]) -> bool:
    return any(IN_USE.search(n) for n in names)


def test_every_destructive_action_is_audited() -> None:
    offenders = sorted(set(_missing(has_audit)) - NO_AUDIT.keys())
    assert not offenders, (
        f"{offenders} delete, archive or retire without calling record_for_owner. "
        "Write the audit row in the same transaction, or add the function to NO_AUDIT with the reason."
    )


def test_every_destructive_action_checks_what_still_depends_on_it() -> None:
    offenders = sorted(set(_missing(has_in_use_check)) - NO_IN_USE_CHECK.keys())
    assert not offenders, (
        f"{offenders} delete, archive or retire without an in-use check. Refuse with a Conflict that "
        "names what still depends on it, or add the function to NO_IN_USE_CHECK with the reason."
    )


def test_the_allow_lists_only_shrink() -> None:
    assert_allow_list("NO_AUDIT", NO_AUDIT, NO_AUDIT_CEILING, _missing(has_audit))
    assert_allow_list("NO_IN_USE_CHECK", NO_IN_USE_CHECK, NO_IN_USE_CEILING, _missing(has_in_use_check))


def test_the_guard_sees_the_known_destructive_actions() -> None:
    found = destructive_functions()
    assert "app/features/catalog/service_authoring.py::delete_exam" in found
    assert "app/features/roster/service_edit.py::delete_trainee" in found
    assert len(found) >= 15


def test_the_checks_tell_a_compliant_action_from_a_bare_one(tmp_path: Path) -> None:
    source = (
        "async def delete_x(s):\n    await exam_in_use(s)\n    await service_audit.record_for_owner(s)\n"
        "async def delete_y(s):\n    await s.execute(1)\n"
    )
    f = tmp_path / "service.py"
    f.write_text(source, encoding="utf-8")
    good, bad = [n for n in ast.parse(source).body]
    assert has_audit(_names_reached(f, good, {})) and has_in_use_check(_names_reached(f, good, {}))
    assert not has_audit(_names_reached(f, bad, {})) and not has_in_use_check(_names_reached(f, bad, {}))
