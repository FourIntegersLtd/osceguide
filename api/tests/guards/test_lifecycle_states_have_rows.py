"""Every status a lifecycle model can hold is a state in the lifecycle matrix, or allowed with a reason.

A new status (say a `paused` org) that no gate was taught about is how sibling
gates come to disagree. This reads the lifecycle slices' status literals and
fails on any that is neither a state in `tests/support/lifecycle_world.STATES`
nor on `NOT_A_GATE` with the reason it gates nothing.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.guards._scan import APP_ROOT, FEATURES_ROOT, parse, rel
from tests.support.lifecycle_world import STATES

#: Which status literals each state stands for, for the completeness guard.
STATE_LITERALS: dict[str, frozenset[str]] = {
    "baseline": frozenset({"active", "trial", "published"}),
    "org_suspended": frozenset({"suspended"}),
    "membership_removed": frozenset({"revoked"}),
    "trainee_revoked": frozenset({"revoked"}),
    "programme_retired": frozenset({"retired"}),
    "exam_retired": frozenset({"retired"}),
    "station_archived": frozenset({"archived"}),
    "entitlement_lapsed": frozenset({"expired"}),
    "account_closed": frozenset({"deleted"}),
    "account_deactivated": frozenset({"deactivated"}),
}


#: Where the lifecycle statuses live: the subjects the matrix covers.
LIFECYCLE_SOURCES = (
    FEATURES_ROOT / "tenancy",
    FEATURES_ROOT / "roster",
    FEATURES_ROOT / "identity",
    FEATURES_ROOT / "catalog",
    FEATURES_ROOT / "entitlements",
    FEATURES_ROOT / "stations",
    APP_ROOT / "core" / "lifecycle.py",
    APP_ROOT / "core" / "account_status.py",
)

#: Status literals that are not a lifecycle state of a gated subject, and why.
NOT_A_GATE: dict[str, str] = {
    "draft": "Before release: a draft station, template, programme or exam is never offered, so nothing "
    "running can meet it (station_not_published, programme_not_active; test_sitting_gates).",
    "invited": "An account or practice access nobody has taken up: there is no session to gate yet.",
    "accepted": "A sign-in step's outcome (identity schemas), not a stored state.",
    "signed_in": "A sign-in step's outcome (identity schemas), not a stored state.",
    "mfa_required": "A sign-in step's outcome (identity schemas), not a stored state.",
    "mfa_enrolment_required": "A sign-in step's outcome (identity schemas), not a stored state.",
    "status": "A column name passed as a sort or filter key, not a value.",
    "all": "A list filter (catalog authoring), not a value.",
    "drafting_station": "Station import job progress: a background job, not access.",
    "drafting_template": "Station import job progress: a background job, not access.",
    "template_ready": "Station import job progress: a background job, not access.",
    "completed": "Station import job progress: a background job, not access.",
    "failed": "Station import job progress: a background job, not access.",
    "open": "A station's content flag (moderation queue): it gates nothing.",
    "resolved": "A station's content flag (moderation queue): it gates nothing.",
}


def _values(literal: str) -> set[str]:
    """`'active'` (a server default) is `active`; `^(a|b)$` (a schema pattern) is `a` and `b`."""
    literal = literal.strip("'\"")
    if literal.startswith("^(") and literal.endswith(")$"):
        return set(literal[2:-2].split("|"))
    return {literal}


def _status_literals(tree: ast.AST) -> set[str]:
    """String constants a module uses as a status: enum members, *_STATUSES sets,
    `status=` arguments and `.status ==` comparisons."""
    found: set[str] = set()

    def strings(node: ast.AST) -> set[str]:
        return {n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.endswith("Status"):
            for item in node.body:
                if isinstance(item, ast.Assign | ast.AnnAssign) and item.value is not None:
                    found |= strings(item.value)
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [t.id for t in targets if isinstance(t, ast.Name)]
            if node.value is not None and any(n.upper().endswith(("STATUSES", "STATUS")) for n in names):
                found |= strings(node.value)
        elif isinstance(node, ast.keyword) and node.arg == "status" and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                found.add(node.value.value)
        elif isinstance(node, ast.Compare):
            sides = [node.left, *node.comparators]
            if any(isinstance(s, ast.Attribute) and s.attr == "status" for s in sides):
                for side in sides:
                    if isinstance(side, ast.Constant) and isinstance(side.value, str):
                        found.add(side.value)
                    elif isinstance(side, ast.Tuple | ast.Set | ast.List):
                        found |= strings(side)
    return found


def _lifecycle_files() -> list[Path]:
    files: list[Path] = []
    for source in LIFECYCLE_SOURCES:
        files.extend([source] if source.is_file() else sorted(source.rglob("*.py")))
    return files


def test_every_lifecycle_status_is_in_the_matrix_or_allowed() -> None:
    covered = set().union(*STATE_LITERALS.values()) | set(NOT_A_GATE)
    missing = {
        literal: rel(path)
        for path in _lifecycle_files()
        for found in _status_literals(parse(path))
        for literal in _values(found)
        if literal not in covered
    }
    assert not missing, (
        "A status with no row in the lifecycle matrix. Add a state for it, or allow it in "
        f"NOT_A_GATE with the reason it gates nothing: {missing}"
    )


def test_every_literal_state_is_a_state_in_the_matrix() -> None:
    assert set(STATE_LITERALS) <= set(STATES)
